# Java mod → Bedrock: experimental pipeline

This is **not** an automatic Java-to-TypeScript translator.

## Supported now
- Read-only JAR inspection (Fabric, Quilt, Forge/NeoForge).
- Copy up to 500 PNG texture assets into a Bedrock resource pack.
- Export a `.mcaddon` containing a `.mcpack` and a conversion report.
- Optionally invoke a **locally supplied** Vineflower JAR to obtain Java source for **manual** porting.

## Run
```bash
python bedrock_converter.py my-mod.jar output.mcaddon
python bedrock_converter.py my-mod.jar output.mcaddon --vineflower /path/to/vineflower.jar --sources-dir ./reviewed-source
python -m unittest tests.test_java_mod_analyzer tests.test_bedrock_converter
```

Vineflower requires Java installed. Run untrusted decompilation only in a sandbox with network disabled and strict resource limits. The command-line Vineflower option is intended for trusted input.

## Manual Bedrock porting
1. Inspect Java source and identify game mechanics.
2. Reimplement compatible mechanics using Bedrock Script API (TypeScript compiled to JavaScript).
3. Add behavior pack JSON definitions and texture/model mappings.
4. Test in Minecraft Bedrock. The generated textures alone will not create functional items or blocks.

No automatic Java bytecode-to-Bedrock conversion is claimed.
