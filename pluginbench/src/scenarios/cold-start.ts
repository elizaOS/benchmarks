import { BenchmarkRunner } from "../runner";

async function main() {
    const runner = new BenchmarkRunner();
    console.log("Running Cold Start Benchmark...");

    try {
        const time = await runner.measure("Cold Start (No Runtime)", async () => {
            await runner.startServer(0);
        });
        console.log(`Cold Start Time: ${time.toFixed(2)}ms`);

        // Validate server is responsive
        await runner.waitForReady();
        console.log("Server is ready and responsive");

    } catch (err) {
        console.error("Benchmark failed:", err);
    } finally {
        await runner.stopServer();
    }
}

main();
