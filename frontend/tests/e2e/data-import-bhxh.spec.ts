import { expect, test, type APIRequestContext, type Page } from "@playwright/test";
import { deflateRawSync, inflateRawSync } from "node:zlib";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { promises as fs } from "node:fs";

const ADMIN_EMAIL = process.env.E2E_EMAIL || "admin@hrms.local";
const ADMIN_PASSWORD = process.env.E2E_PASSWORD || "Hrms@2026";

const CONTRACT_TEMPLATE_BASE64 =
  "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";

const INSURANCE_TEMPLATE_BASE64 =
  "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";

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

function patchSheet(base64: string, replacements: Array<[string, string]>) {
  const entries = parseZip(Buffer.from(base64, "base64"));
  const sheet = entries.find((entry) => entry.name === "xl/worksheets/sheet1.xml");
  if (!sheet) throw new Error("sheet1.xml not found");
  let xml = sheet.data.toString("utf8");
  for (const [from, to] of replacements) {
    xml = xml.replaceAll(from, to);
  }
  sheet.data = Buffer.from(xml, "utf8");
  return buildZip(entries);
}

async function writeTempXlsx(name: string, buffer: Buffer) {
  const path = join(tmpdir(), name);
  await fs.writeFile(path, buffer);
  return path;
}

async function createProbeEmployee(request: APIRequestContext, token: string, stamp: string) {
  const seqResp = await request.get("/api/v1/employee-code-sequences");
  expect(seqResp.status()).toBe(200);
  const sequences = (await seqResp.json()) as Array<{ id: number; code: string }>;
  const sys1 = sequences.find((sequence) => sequence.code === "SYS1");
  expect(sys1).toBeTruthy();

  const employeeSeq = 900000 + Number(stamp.slice(-4));
  const idNumber = `E2EIMP${stamp}`;
  const createResp = await request.post("/api/v1/employees", {
    headers: { Authorization: `Bearer ${token}` },
    data: {
      employee_seq: employeeSeq,
      employee_code_sequence_id: sys1!.id,
      full_name: `E2E Import BHXH ${stamp}`,
      last_name: "E2E",
      first_name: `Import ${stamp}`,
      date_of_birth: "1990-01-01",
      gender: "male",
      nationality_id: 1,
      id_number: idNumber,
      id_issued_on: "2020-01-01",
      id_issued_by: "Cuc Canh sat",
      status: "official",
      start_date: "2026-01-01",
    },
  });
  expect(createResp.status()).toBe(201);
  return await createResp.json() as { id: number; employee_seq: number; display_code: string };
}

test("data import UI uploads computed contract and insurance profile end-to-end", async ({ page, request }) => {
  const token = await adminToken(request);
  const stamp = String(Date.now());
  const employee = await createProbeEmployee(request, token, stamp);
  const contractNumber = `E2E-HTTP-BHXH-C-${stamp.slice(-6)}`;
  const bhxhCode = `E2EHTTPBHXH_${stamp.slice(-6)}`;

  const contractFile = await writeTempXlsx(
    `contract-import-${stamp}.xlsx`,
    patchSheet(CONTRACT_TEMPLATE_BASE64, [
      ["9791", String(employee.employee_seq)],
      ["HTTP-BHXH-C-9791", contractNumber],
    ]),
  );
  const insuranceFile = await writeTempXlsx(
    `insurance-import-${stamp}.xlsx`,
    patchSheet(INSURANCE_TEMPLATE_BASE64, [
      ["9791", String(employee.employee_seq)],
      ["HTTPBHXH_9791_BH", bhxhCode],
    ]),
  );

  try {
    await page.setViewportSize({ width: 1600, height: 1200 });
    await login(page, "/data/import");
    await page.waitForLoadState("networkidle");

    await page.getByRole("tab", { name: "Hợp đồng" }).click();
    const contractImport = page.waitForResponse((response) =>
      response.url().includes("/api/v1/imports/contracts") &&
      response.request().method() === "POST",
    );
    await page.locator('input[type="file"]').first().setInputFiles(contractFile);
    await page.getByRole("button", { name: "Bắt đầu import" }).click();
    expect((await contractImport).status()).toBe(200);
    const contractResult = page.locator(".import-result-card").first();
    await expect(contractResult.getByText("Thành công: 1")).toBeVisible();
    await expect(contractResult.getByText("Lỗi: 0")).toBeVisible();

    await page.getByRole("tab", { name: "Bảo hiểm" }).click();
    const insuranceImport = page.waitForResponse((response) =>
      response.url().includes("/api/v1/imports/insurance") &&
      response.request().method() === "POST",
    );
    await page.locator('input[type="file"]').first().setInputFiles(insuranceFile);
    await page.getByRole("button", { name: "Bắt đầu import" }).click();
    expect((await insuranceImport).status()).toBe(200);
    const insuranceResult = page.locator(".import-result-card").first();
    await expect(insuranceResult.getByText("Thành công: 1")).toBeVisible();
    await expect(insuranceResult.getByText("Lỗi: 0")).toBeVisible();

    await page.goto(`/employees/${employee.id}`);
    await page.waitForLoadState("networkidle");

    await page.getByRole("tab", { name: "Hợp đồng" }).click();
    await expect(page.locator(".contract-card").filter({ hasText: contractNumber }).first()).toBeVisible();
    await expect(page.locator(".contract-card").filter({ hasText: "Theo nhóm vị trí + bậc" }).first()).toBeVisible();
    await expect(page.locator(".contract-card").filter({ hasText: "OFFICE_STAFF" }).first()).toBeVisible();

    await page.getByRole("tab", { name: "Bảo hiểm" }).click();
    await expect(page.getByText(bhxhCode)).toBeVisible();
    await expect(page.getByText("5.423.400")).toBeVisible();
    await expect(page.getByText("(Tính tự động)")).toBeVisible();
  } finally {
    await request.delete(`/api/v1/employees/${employee.id}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    await fs.unlink(contractFile).catch(() => undefined);
    await fs.unlink(insuranceFile).catch(() => undefined);
  }
});
