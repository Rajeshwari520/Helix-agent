// Builds the React app into ../app/static/ui/ (app.js + app.css), which FastAPI serves at /agent and /dashboard.
//   npm run build   -> minified production bundle (commit the result so the app runs without Node)
//   npm run dev     -> rebuilds on every save; refresh the browser
import * as esbuild from "esbuild";

const watch = process.argv.includes("--watch");
const options = {
  entryPoints: ["src/main.jsx"],
  bundle: true,
  outfile: "../app/static/ui/app.js",
  jsx: "automatic",
  target: ["es2020"],
  minify: !watch,
  sourcemap: watch,
  legalComments: "none",
  define: { "process.env.NODE_ENV": JSON.stringify(watch ? "development" : "production") },
  logLevel: "info",
};

if (watch) {
  const ctx = await esbuild.context(options);
  await ctx.watch();
  console.log("Watching src/ ... (Ctrl+C to stop). Keep uvicorn running and refresh the browser.");
} else {
  await esbuild.build(options);
}
