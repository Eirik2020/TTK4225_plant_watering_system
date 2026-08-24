# Project report

The LaTeX source and generated report files are contained in this directory.

## Build

From the `latex` directory on Windows:

```powershell
.\scripts\build.ps1
```

The script uses a native `latexmk` installation when one is available and
otherwise falls back to a pinned Docker image. Force a particular mode with:

```powershell
.\scripts\build.ps1 -Native
.\scripts\build.ps1 -Docker
```

Temporary compiler files go to `build/`; the finished PDF is copied to
`dist/report.pdf`. Remove generated output with:

```powershell
.\scripts\build.ps1 -Clean
```

For a native build, install MiKTeX or TeX Live with `latexmk`, LuaLaTeX, and
Biber. MiKTeX may ask to install missing packages during the first build.

## VS Code

Install the recommended LaTeX Workshop extension. The repository settings
build on save with LuaLaTeX, place output in `latex/build`, and show the PDF in
a VS Code tab. Useful shortcuts are `Ctrl+Alt+B` to build and `Ctrl+Alt+V` to
view the PDF.

## Start writing

1. Replace the placeholders in `metadata.tex`.
2. Rewrite `frontmatter/abstract.tex` after the report is complete.
3. Fill in the files under `chapters/`.
4. Add sources to `references/references.bib` and cite them with `\cite{key}`.
5. Put plots, diagrams, and photographs in `figures/`.
6. Update the final pin assignment in `appendices/a-pinout.tex`.

The current text and measurement values are prompts, not project results.
