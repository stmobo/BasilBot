import resolve from '@rollup/plugin-node-resolve';
import del from 'rollup-plugin-delete';
import commonjs from '@rollup/plugin-commonjs';
import typescript from '@rollup/plugin-typescript';
import outputManifest from 'rollup-plugin-output-manifest';
import { terser } from 'rollup-plugin-terser';

export default {
    input: "web-src/index.ts",
    output: [
        {
            dir: "./build/js/",
            format: "iife",
            name: "Basil",
            entryFileNames: "[name]-[hash].js"
        }
    ],
    plugins: [
        del({ targets: "build/js/*" }),
        resolve(),
        commonjs(),
        typescript({ tsconfig: "web-src/tsconfig.json" }),
        terser(),
        outputManifest({ fileName: "base_manifest.json" }),
    ]
}