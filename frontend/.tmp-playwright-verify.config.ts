export default {
  testDir: "./tests/e2e",
  reporter: [["list"]],
  use: {
    baseURL: process.env.BASE_URL || "http://127.0.0.1:4174",
    browserName: "chromium",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "off",
    actionTimeout: 10_000,
    navigationTimeout: 30_000,
    launchOptions: {
      args: ["--no-sandbox", "--disable-setuid-sandbox"],
    },
    viewport: {
      width: 1180,
      height: 900,
    },
  },
  projects: [
    {
      name: "chromium",
      use: {
        browserName: "chromium",
      },
    },
  ],
};
