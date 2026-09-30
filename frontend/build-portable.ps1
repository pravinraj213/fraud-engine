$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    $sentinelCompiler = Join-Path $PSScriptRoot 'node_modules/@esbuild/win32-x64/esbuild.exe'
    if (-not (Test-Path -LiteralPath $sentinelCompiler)) { throw 'Run npm install first (npm install --ignore-scripts if child-process creation is restricted).' }
    & $sentinelCompiler src/main.jsx --bundle --minify --format=esm --jsx=automatic --outdir=dist/assets --entry-names=app
    if ($LASTEXITCODE -ne 0) { throw 'Frontend compilation failed.' }
    $sentinelHtml = Get-Content index.html -Raw
    $sentinelHtml.Replace('/src/main.jsx','/assets/app.js').Replace('</head>','<link rel="stylesheet" href="/assets/app.css" /></head>') | Set-Content dist/index.html -Encoding utf8
    if (Test-Path -LiteralPath 'public') { Copy-Item -Path 'public/*' -Destination 'dist' -Recurse -Force }
    Write-Output 'Browser-ready bundle written to frontend/dist.'
} finally { Pop-Location }
