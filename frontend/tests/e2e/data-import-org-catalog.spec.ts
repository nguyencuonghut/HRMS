import { expect, test, type APIRequestContext, type Page } from "@playwright/test";
import { deflateRawSync, inflateRawSync } from "node:zlib";
import { tmpdir } from "node:os";
import { basename, join } from "node:path";
import { promises as fs } from "node:fs";

const ADMIN_EMAIL = process.env.E2E_EMAIL || "admin@hrms.local";
const ADMIN_PASSWORD = process.env.E2E_PASSWORD || "Hrms@2026";

type ZipEntry = {
  name: string;
  method: number;
  flags: number;
  modTime: number;
  modDate: number;
  versionMadeBy: number;
  versionNeeded: number;
  internalAttrs: number;
  externalAttrs: number;
  extraLocal: Buffer;
  extraCentral: Buffer;
  comment: Buffer;
  data: Buffer;
};

async function login(page: Page, redirect = "/data/import") {
  await page.goto(`/login?redirect=${encodeURIComponent(redirect)}`);
  await page.getByLabel("Email").fill(ADMIN_EMAIL);
  await page.getByPlaceholder("Nhập mật khẩu").fill(ADMIN_PASSWORD);
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await page.waitForURL(new RegExp(redirect.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
}

async function adminToken(request: APIRequestContext) {
  const response = await request.post("/api/v1/auth/login", {
    data: { email: ADMIN_EMAIL, password: ADMIN_PASSWORD },
  });
  expect(response.status()).toBe(200);
  const body = await response.json();
  return body.access_token as string;
}

function makeCrcTable() {
  const table = new Uint32Array(256);
  for (let n = 0; n < 256; n += 1) {
    let c = n;
    for (let k = 0; k < 8; k += 1) {
      c = (c & 1) ? (0xedb88320 ^ (c >>> 1)) : (c >>> 1);
    }
    table[n] = c >>> 0;
  }
  return table;
}

const CRC_TABLE = makeCrcTable();

function crc32(buffer: Buffer) {
  let crc = 0xffffffff;
  for (const byte of buffer) {
    crc = CRC_TABLE[(crc ^ byte) & 0xff] ^ (crc >>> 8);
  }
  return (crc ^ 0xffffffff) >>> 0;
}

function parseZip(buffer: Buffer): ZipEntry[] {
  const eocdSig = 0x06054b50;
  let eocdOffset = -1;
  for (let i = buffer.length - 22; i >= 0; i -= 1) {
    if (buffer.readUInt32LE(i) === eocdSig) {
      eocdOffset = i;
      break;
    }
  }
  if (eocdOffset < 0) throw new Error("EOCD not found");

  const totalEntries = buffer.readUInt16LE(eocdOffset + 10);
  const centralDirOffset = buffer.readUInt32LE(eocdOffset + 16);
  const entries: ZipEntry[] = [];
  let offset = centralDirOffset;

  for (let i = 0; i < totalEntries; i += 1) {
    if (buffer.readUInt32LE(offset) !== 0x02014b50) throw new Error("Invalid central directory");
    const versionMadeBy = buffer.readUInt16LE(offset + 4);
    const versionNeeded = buffer.readUInt16LE(offset + 6);
    const flags = buffer.readUInt16LE(offset + 8);
    const method = buffer.readUInt16LE(offset + 10);
    const modTime = buffer.readUInt16LE(offset + 12);
    const modDate = buffer.readUInt16LE(offset + 14);
    const compressedSize = buffer.readUInt32LE(offset + 20);
    const fileNameLength = buffer.readUInt16LE(offset + 28);
    const extraLength = buffer.readUInt16LE(offset + 30);
    const commentLength = buffer.readUInt16LE(offset + 32);
    const internalAttrs = buffer.readUInt16LE(offset + 36);
    const externalAttrs = buffer.readUInt32LE(offset + 38);
    const localOffset = buffer.readUInt32LE(offset + 42);
    const name = buffer.slice(offset + 46, offset + 46 + fileNameLength).toString("utf8");
    const extraCentral = buffer.slice(offset + 46 + fileNameLength, offset + 46 + fileNameLength + extraLength);
    const comment = buffer.slice(
      offset + 46 + fileNameLength + extraLength,
      offset + 46 + fileNameLength + extraLength + commentLength,
    );

    if (buffer.readUInt32LE(localOffset) !== 0x04034b50) throw new Error("Invalid local header");
    const localNameLength = buffer.readUInt16LE(localOffset + 26);
    const localExtraLength = buffer.readUInt16LE(localOffset + 28);
    const extraLocal = buffer.slice(
      localOffset + 30 + localNameLength,
      localOffset + 30 + localNameLength + localExtraLength,
    );
    const dataOffset = localOffset + 30 + localNameLength + localExtraLength;
    const compressedData = buffer.slice(dataOffset, dataOffset + compressedSize);
    const data = method === 8 ? inflateRawSync(compressedData) : Buffer.from(compressedData);

    entries.push({
      name,
      method,
      flags,
      modTime,
      modDate,
      versionMadeBy,
      versionNeeded,
      internalAttrs,
      externalAttrs,
      extraLocal,
      extraCentral,
      comment,
      data,
    });

    offset += 46 + fileNameLength + extraLength + commentLength;
  }
  return entries;
}

function buildZip(entries: ZipEntry[]) {
  const localParts: Buffer[] = [];
  const centralParts: Buffer[] = [];
  let localOffset = 0;

  for (const entry of entries) {
    const fileName = Buffer.from(entry.name, "utf8");
    const compressedData = entry.method === 8 ? deflateRawSync(entry.data) : entry.data;
    const crc = crc32(entry.data);

    const localHeader = Buffer.alloc(30);
    localHeader.writeUInt32LE(0x04034b50, 0);
    localHeader.writeUInt16LE(entry.versionNeeded, 4);
    localHeader.writeUInt16LE(entry.flags, 6);
    localHeader.writeUInt16LE(entry.method, 8);
    localHeader.writeUInt16LE(entry.modTime, 10);
    localHeader.writeUInt16LE(entry.modDate, 12);
    localHeader.writeUInt32LE(crc, 14);
    localHeader.writeUInt32LE(compressedData.length, 18);
    localHeader.writeUInt32LE(entry.data.length, 22);
    localHeader.writeUInt16LE(fileName.length, 26);
    localHeader.writeUInt16LE(entry.extraLocal.length, 28);
    localParts.push(localHeader, fileName, entry.extraLocal, compressedData);

    const centralHeader = Buffer.alloc(46);
    centralHeader.writeUInt32LE(0x02014b50, 0);
    centralHeader.writeUInt16LE(entry.versionMadeBy, 4);
    centralHeader.writeUInt16LE(entry.versionNeeded, 6);
    centralHeader.writeUInt16LE(entry.flags, 8);
    centralHeader.writeUInt16LE(entry.method, 10);
    centralHeader.writeUInt16LE(entry.modTime, 12);
    centralHeader.writeUInt16LE(entry.modDate, 14);
    centralHeader.writeUInt32LE(crc, 16);
    centralHeader.writeUInt32LE(compressedData.length, 20);
    centralHeader.writeUInt32LE(entry.data.length, 24);
    centralHeader.writeUInt16LE(fileName.length, 28);
    centralHeader.writeUInt16LE(entry.extraCentral.length, 30);
    centralHeader.writeUInt16LE(entry.comment.length, 32);
    centralHeader.writeUInt16LE(0, 34);
    centralHeader.writeUInt16LE(entry.internalAttrs, 36);
    centralHeader.writeUInt32LE(entry.externalAttrs, 38);
    centralHeader.writeUInt32LE(localOffset, 42);
    centralParts.push(centralHeader, fileName, entry.extraCentral, entry.comment);

    localOffset += localHeader.length + fileName.length + entry.extraLocal.length + compressedData.length;
  }

  const centralDirectory = Buffer.concat(centralParts);
  const localData = Buffer.concat(localParts);
  const eocd = Buffer.alloc(22);
  eocd.writeUInt32LE(0x06054b50, 0);
  eocd.writeUInt16LE(0, 4);
  eocd.writeUInt16LE(0, 6);
  eocd.writeUInt16LE(entries.length, 8);
  eocd.writeUInt16LE(entries.length, 10);
  eocd.writeUInt32LE(centralDirectory.length, 12);
  eocd.writeUInt32LE(localData.length, 16);
  eocd.writeUInt16LE(0, 20);
  return Buffer.concat([localData, centralDirectory, eocd]);
}

function patchWorkbookXml(buffer: Buffer, replacements: Array<[string, string]>) {
  const entries = parseZip(buffer);
  for (const entry of entries) {
    if (!entry.name.endsWith(".xml")) continue;
    let xml = entry.data.toString("utf8");
    for (const [from, to] of replacements) {
      xml = xml.replaceAll(from, to);
    }
    entry.data = Buffer.from(xml, "utf8");
  }
  return buildZip(entries);
}

async function writeTempXlsx(name: string, buffer: Buffer) {
  const path = join(tmpdir(), name);
  await fs.writeFile(path, buffer);
  return path;
}

async function downloadTemplate(request: APIRequestContext, token: string, url: string) {
  const response = await request.get(url, {
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(response.status()).toBe(200);
  return Buffer.from(await response.body());
}

async function uploadWithinPanel(page: Page, panelIndex: number, filePath: string) {
  const panel = page.locator(".import-panel").nth(panelIndex);
  await panel.locator('input[type="file"]').setInputFiles(filePath);
  await expect(panel.getByText(basename(filePath))).toBeVisible();
  await panel.getByRole("button", { name: "Bắt đầu import" }).click();
  await expect(panel.getByText("Thành công:")).toContainText("1");
  await expect(panel.getByText("Lỗi:")).toContainText("0");
}

test("data import page supports org catalog import in dependency order", async ({ page, request }) => {
  const token = await adminToken(request);
  const stamp = String(Date.now()).slice(-6);
  const deptCode = `IMPD${stamp}`;
  const deptName = `Phòng import ${stamp}`;
  const titleCode = `IMJT${stamp}`;
  const titleName = `Chức danh import ${stamp}`;
  const posCode = `IMPV${stamp}`;
  const posName = `Vị trí import ${stamp}`;

  const deptTemplate = await downloadTemplate(request, token, "/api/v1/imports/departments/template");
  const titleTemplate = await downloadTemplate(request, token, "/api/v1/imports/job-titles/template");
  const positionTemplate = await downloadTemplate(request, token, "/api/v1/imports/job-positions/template");

  const deptFile = await writeTempXlsx(
    `dept-import-${stamp}.xlsx`,
    patchWorkbookXml(deptTemplate, [
      ["HCNS", deptCode],
      ["Phòng Hành chính nhân sự", deptName],
      [">HC<", `>${deptCode.slice(0, 5)}<`],
      [">10<", ">11<"],
    ]),
  );
  const titleFile = await writeTempXlsx(
    `jt-import-${stamp}.xlsx`,
    patchWorkbookXml(titleTemplate, [
      ["TPKD", titleCode],
      ["Trưởng phòng kinh doanh", titleName],
      [">4<", ">6<"],
    ]),
  );
  const positionFile = await writeTempXlsx(
    `pos-import-${stamp}.xlsx`,
    patchWorkbookXml(positionTemplate, [
      ["KD_NV_01", posCode],
      ["Nhân viên kinh doanh miền Bắc", posName],
      [">KD<", `>${deptCode}<`],
      [">NVKD<", `>${titleCode}<`],
      ["Chăm sóc đại lý", `Mô tả ${stamp}`],
      ["Kỹ năng bán hàng", `Yêu cầu ${stamp}`],
    ]),
  );

  await login(page);

  const tabs = await page.getByRole("tab").allTextContents();
  expect(tabs.slice(0, 7)).toEqual([
    "Phòng ban",
    "Chức danh",
    "Vị trí công việc",
    "Nhân viên",
    "Nghỉ phép",
    "Hợp đồng",
    "Bảo hiểm",
  ]);

  await page.getByRole("tab", { name: "Phòng ban" }).click();
  await uploadWithinPanel(page, 0, deptFile);

  await page.getByRole("tab", { name: "Chức danh" }).click();
  await uploadWithinPanel(page, 1, titleFile);

  await page.getByRole("tab", { name: "Vị trí công việc" }).click();
  await uploadWithinPanel(page, 2, positionFile);

});

test("job title tab downloads and uploads the matching template via UI", async ({ page }) => {
  await login(page);

  await page.getByRole("tab", { name: "Chức danh" }).click();
  const panel = page.locator(".import-panel").nth(1);

  const apiRequests: Array<{ method: string; url: string }> = [];
  page.on("request", (request) => {
    const url = request.url();
    if (url.includes("/api/v1/imports/")) {
      apiRequests.push({ method: request.method(), url });
    }
  });

  const downloadPromise = page.waitForEvent("download");
  await panel.getByRole("button", { name: "Tải file mẫu .xlsx" }).click();
  const download = await downloadPromise;
  const filePath = join(tmpdir(), await download.suggestedFilename());
  await download.saveAs(filePath);

  const importResponsePromise = page.waitForResponse((response) =>
    response.url().includes("/api/v1/imports/job-titles") && response.request().method() === "POST",
  );

  await panel.locator('input[type="file"]').setInputFiles(filePath);
  await expect(panel.getByText(basename(filePath))).toBeVisible();
  await panel.getByRole("button", { name: "Bắt đầu import" }).click();

  const importResponse = await importResponsePromise;
  expect(importResponse.status()).toBe(200);
  const body = await importResponse.json();
  expect(body.failed).toBe(0);
  expect(body.success).toBeGreaterThan(0);

  await expect(panel.getByText("Thành công:")).not.toContainText("0");
  await expect(panel.getByText("Lỗi:")).toContainText("0");

  expect(apiRequests).toEqual([
    { method: "GET", url: "http://127.0.0.1:5173/api/v1/imports/job-titles/template" },
    { method: "POST", url: "http://127.0.0.1:5173/api/v1/imports/job-titles" },
  ]);
});
