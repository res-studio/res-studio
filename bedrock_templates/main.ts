// Starter template for a MANUAL Bedrock Script API port.
// This is not generated from Java code.
// Configure a behavior pack manifest and @minecraft/server dependency separately.
import { world } from "@minecraft/server";

world.afterEvents.playerSpawn.subscribe((event) => {
  if (event.initialSpawn) {
    console.warn("[RES] Bedrock script starter loaded");
  }
});
