/* FACEIT Voice adapter. Only the bundled repair code is executed. */
function read(path) {
    const f = std.open(path, 'rb');
    if (!f) throw Error('Cannot open input demo');
    try {
        if (f.seek(0, std.SEEK_END) !== 0) throw Error('Cannot seek input');
        const size = f.tell();
        if (size < 16 || size > 2147483647) throw Error('Unsupported demo size (16 bytes to 2 GiB)');
        f.seek(0, std.SEEK_SET);
        const bytes = new Uint8Array(size);
        if (f.read(bytes.buffer, 0, size) !== size) throw Error('Incomplete input read');
        return bytes;
    } finally { f.close(); }
}
try {
    if (scriptArgs.length !== 3) throw Error('Expected input and output paths');
    // Only fix the startup crash; do not change unrelated game-event text.
    const result = globalThis.DemoFix.fixDemo(read(scriptArgs[1]), {sanitizeText: false});
    if (result.report.warnings.length ||
        (result.report.crashFix.needed && !result.report.crashFix.applied)) {
        throw Error(result.report.warnings.join('; ') || 'Crash repair could not be applied');
    }
    if (result.changed) {
        const out = std.open(scriptArgs[2], 'wb');
        if (!out) throw Error('Cannot open output demo');
        try {
            for (const part of result.parts) {
                if (out.write(part.buffer, part.byteOffset, part.byteLength) !== part.byteLength)
                    throw Error('Incomplete output write');
            }
            out.flush();
            if (out.error()) throw Error('Cannot flush output demo');
        } finally { out.close(); }
    }
    console.log(JSON.stringify(result.report));
} catch (e) {
    std.err.puts(String(e) + '\n');
    std.exit(1);
}
