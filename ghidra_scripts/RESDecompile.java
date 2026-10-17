// RES Studio Ghidra headless script. Run only inside a trusted, isolated worker.
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import java.io.File;
import java.io.PrintWriter;

public class RESDecompile extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 1) throw new IllegalArgumentException("Output path required");
        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        int count = 0;
        try (PrintWriter out = new PrintWriter(new File(args[0]), "UTF-8")) {
            FunctionIterator functions = currentProgram.getFunctionManager().getFunctions(true);
            while (functions.hasNext() && count < 50 && !monitor.isCancelled()) {
                Function fn = functions.next();
                DecompileResults result = decompiler.decompileFunction(fn, 10, monitor);
                if (result.decompileCompleted() && result.getDecompiledFunction() != null) {
                    out.println("// " + fn.getName() + " @ " + fn.getEntryPoint());
                    out.println(result.getDecompiledFunction().getC());
                    count++;
                }
            }
        } finally {
            decompiler.dispose();
        }
    }
}
