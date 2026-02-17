import { BenchmarkRunner } from "../runner";

async function main() {
    const runner = new BenchmarkRunner();
    console.log("Running Hot Reload Benchmark (Simulation)...");

    // Mock runtime would be needed for real plugin ops, but here we measure failures or mock responses if we could mock.
    // Since we don't have easy mocking in this process (it runs separate from vitest), we will just measure the HTTP call latency.
    // We expect 500s if no runtime, but we measure the Round Trip Time.

    try {
        await runner.startServer(0);

        // Baseline request
        await runner.measure("API Ping", async () => {
            await runner.http("GET", "/api/status");
        });

        // Simulated Eject (will fail but we measure overhead)
        await runner.measure("Eject Latency (Expected Fail)", async () => {
            await runner.http("POST", "/api/plugins/some-plugin/eject");
        });

        // Simulated Sync
        await runner.measure("Sync Latency (Expected Fail)", async () => {
            await runner.http("POST", "/api/plugins/some-plugin/sync");
        });

    } catch (err) {
        console.error("Benchmark failed:", err);
    } finally {
        await runner.stopServer();
    }
}

main();
