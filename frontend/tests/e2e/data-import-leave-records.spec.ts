import { expect, test, type APIRequestContext, type Page } from "@playwright/test";
import { deflateRawSync, inflateRawSync } from "node:zlib";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { promises as fs } from "node:fs";

const ADMIN_EMAIL = process.env.E2E_EMAIL || "admin@hrms.local";
const ADMIN_PASSWORD = process.env.E2E_PASSWORD || "Hrms@2026";
const IMPORT_YEAR = 2026;

const LEAVE_TEMPLATE_BASE64 =
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

async function employeeCodeSequenceId(request: APIRequestContext) {
  const response = await request.get("/api/v1/employee-code-sequences");
  expect(response.status()).toBe(200);
  const sequences = (await response.json()) as Array<{ id: number; code: string }>;
  const sys1 = sequences.find((sequence) => sequence.code === "SYS1");
  expect(sys1).toBeTruthy();
  return sys1!.id;
}

async function createProbeEmployee(
  request: APIRequestContext,
  token: string,
  sequenceId: number,
  {
    stamp,
    employeeSeq,
    suffix,
    status,
  }: {
    stamp: string;
    employeeSeq: number;
    suffix: string;
    status: "official" | "resigned";
  },
) {
  const shortIdNumber = `E2EL${suffix[0]}${stamp.slice(-8)}`;
  const createResp = await request.post("/api/v1/employees", {
    headers: { Authorization: `Bearer ${token}` },
    data: {
      employee_seq: employeeSeq,
      employee_code_sequence_id: sequenceId,
      full_name: `E2E Leave Import ${suffix} ${stamp}`,
      last_name: "E2E",
      first_name: `Leave ${suffix}`,
      date_of_birth: "1990-01-01",
      gender: "male",
      nationality_id: 1,
      id_number: shortIdNumber,
      id_issued_on: "2020-01-01",
      id_issued_by: "Cuc Canh sat",
      status,
      start_date: `${IMPORT_YEAR}-01-01`,
      resigned_date: status === "resigned" ? `${IMPORT_YEAR}-12-31` : null,
    },
  });
  expect(createResp.status()).toBe(201);
  return await createResp.json() as { id: number; display_code: string; full_name: string };
}

test("data import UI links leave records to entitlements for official and resigned employees", async ({
  page,
  request,
}) => {
  const token = await adminToken(request);
  const stamp = String(Date.now());
  const sequenceId = await employeeCodeSequenceId(request);
  const activeSeq = 910000 + Number(stamp.slice(-3));
  const resignedSeq = activeSeq + 1;

  const activeEmployee = await createProbeEmployee(request, token, sequenceId, {
    stamp,
    employeeSeq: activeSeq,
    suffix: "ACTIVE",
    status: "official",
  });
  const resignedEmployee = await createProbeEmployee(request, token, sequenceId, {
    stamp,
    employeeSeq: resignedSeq,
    suffix: "RESIGNED",
    status: "resigned",
  });

  const leaveFile = await writeTempXlsx(
    `leave-import-${stamp}.xlsx`,
    patchSheet(LEAVE_TEMPLATE_BASE64, [
      ["EMPSEQ1", String(activeSeq)],
      ["EMPSEQ2", String(resignedSeq)],
      ["01/06/2096", `01/06/${IMPORT_YEAR}`],
      ["03/06/2096", `03/06/${IMPORT_YEAR}`],
      ["05/06/2096", `05/06/${IMPORT_YEAR}`],
    ]),
  );

  try {
    await page.setViewportSize({ width: 1600, height: 1200 });
    await login(page, "/data/import");
    await page.waitForLoadState("networkidle");

    await page.getByRole("tab", { name: "Nghỉ phép" }).click();
    const leaveImportPanel = page.locator(".import-panel").nth(1);
    const importResponse = page.waitForResponse((response) =>
      response.url().includes("/api/v1/imports/leave-records") &&
      response.request().method() === "POST",
    );
    await leaveImportPanel.locator('input[type="file"]').setInputFiles(leaveFile);
    await leaveImportPanel.getByRole("button", { name: "Bắt đầu import" }).click();
    expect((await importResponse).status()).toBe(200);
    const importResult = leaveImportPanel.locator(".import-result-card");
    await expect(importResult.getByText("Thành công: 2")).toBeVisible();
    await expect(importResult.getByText("Lỗi: 0")).toBeVisible();

    await page.goto("/leaves");
    await page.waitForLoadState("networkidle");
    await page.getByPlaceholder("Tìm tên nhân viên...").fill(activeEmployee.full_name);
    await page.getByRole("button", { name: "Lọc" }).click();
    const activeRow = page.locator("tr").filter({ hasText: activeEmployee.full_name }).first();
    await expect(activeRow).toBeVisible();
    await expect(activeRow).toContainText("Phép năm");
    await expect(activeRow).toContainText("3");

    await page.getByPlaceholder("Tìm tên nhân viên...").fill(resignedEmployee.full_name);
    await page.getByRole("button", { name: "Lọc" }).click();
    const resignedRow = page.locator("tr").filter({ hasText: resignedEmployee.full_name }).first();
    await expect(resignedRow).toBeVisible();
    await expect(resignedRow).toContainText("1");

    await page.goto("/leave-entitlements");
    await page.waitForLoadState("networkidle");
    await page.getByPlaceholder("Tìm tên nhân viên...").fill(activeEmployee.full_name);
    await page.getByRole("button", { name: "Lọc" }).click();
    const activeEntitlementRow = page.locator("tr").filter({ hasText: activeEmployee.full_name }).first();
    await expect(activeEntitlementRow).toBeVisible();
    await expect(activeEntitlementRow).toContainText("3");

    await page.getByPlaceholder("Tìm tên nhân viên...").fill(resignedEmployee.full_name);
    await page.getByRole("button", { name: "Lọc" }).click();
    const resignedEntitlementRow = page.locator("tr").filter({ hasText: resignedEmployee.full_name }).first();
    await expect(resignedEntitlementRow).toBeVisible();
    await expect(resignedEntitlementRow).toContainText("1");
  } finally {
    await request.delete(`/api/v1/employees/${activeEmployee.id}`, {
      headers: { Authorization: `Bearer ${token}` },
    }).catch(() => undefined);
    await request.delete(`/api/v1/employees/${resignedEmployee.id}`, {
      headers: { Authorization: `Bearer ${token}` },
    }).catch(() => undefined);
    await fs.unlink(leaveFile).catch(() => undefined);
  }
});
