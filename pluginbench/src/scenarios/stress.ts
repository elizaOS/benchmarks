import { BenchmarkRunner } from "../runner";

async function main() {
    const runner = new BenchmarkRunner();
    console.log("Running Stress Test Benchmark...");

    const mockPluginManager = {
        installPlugin: async (name: string) => {
            // Simulate some async work (e.g. 10-50ms)
            const delay = Math.floor(Math.random() * 40) + 10;
            await new Promise(r => setTimeout(r, delay));
            return { success: true, pluginName: name, requiresRestart: false };
        },
        ejectPlugin: async () => ({ success: true, requiresRestart: true }),
        syncPlugin: async () => ({ success: true, requiresRestart: true }),
        reinjectPlugin: async () => ({ success: true, requiresRestart: true }),
        listEjectedPlugins: async () => ([]),
        refreshRegistry: async () => { },
        listInstalledPlugins: async () => ([]),
        getRegistryPlugin: async () => null,
        searchRegistry: async () => [],
        uninstallPlugin: async () => ({ success: true }),
    };

    const mockRuntime = {
        getService: (type: string) => {
            if (type === "plugin_manager") return mockPluginManager;
            return null;
        },
        character: { name: "StressAgent" },
        agentId: "stress-id",
    };

    try {
        await runner.startServer(0, mockRuntime);

        const CONCURRENCY = 50;
        const TOTAL_REQUESTS = 200;

        console.log(`Starting ${TOTAL_REQUESTS} requests with concurrency ${CONCURRENCY}...`);

        await runner.measure("Concurrent Install Requests", async () => {
            const promises: Promise<any>[] = [];
            for (let i = 0; i < TOTAL_REQUESTS; i++) {
                const p = runner.http("POST", "/api/plugins/install", {
                    name: `@elizaos/plugin-stress-${i}`
                });
                promises.push(p);

                if (promises.length >= CONCURRENCY) {
                    await Promise.all(promises);
                    promises.length = 0;
                }
            }
            if (promises.length > 0) {
                await Promise.all(promises);
            }
        });

    } catch (err) {
        console.error("Benchmark failed:", err);
    } finally {
        await runner.stopServer();
    }
}

main();
