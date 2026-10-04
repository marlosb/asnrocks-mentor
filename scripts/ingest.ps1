<#
.SYNOPSIS
    Lê os segredos de secrets.txt, exporta como variáveis de ambiente e roda o
    script de ingestão do acervo de aulas no Qdrant (scripts/ingest.py).

    Pressupõe que o Qdrant já está rodando (ex.: `.\scripts\start-agent.ps1`
    em outro terminal, ou `docker compose up -d qdrant`).

.EXAMPLE
    .\scripts\ingest.ps1
    .\scripts\ingest.ps1 -Origem .\transcrições -Colecao aulas
#>

param(
    [string]$SecretsFile = (Join-Path $PSScriptRoot "..\secrets.txt"),
    [string]$Origem = (Join-Path $PSScriptRoot "..\transcrições"),
    [string]$Colecao = "aulas"
)

$ErrorActionPreference = "Stop"
$raizProjeto = Resolve-Path (Join-Path $PSScriptRoot "..")

if (-not (Test-Path $SecretsFile)) {
    Write-Error "Arquivo de segredos não encontrado: $SecretsFile (copie a partir de um modelo e preencha nome/endpoint/key do modelo)."
    exit 1
}

Write-Host "Lendo segredos de $SecretsFile..."
Get-Content $SecretsFile | ForEach-Object {
    $linha = $_.Trim()
    if ($linha -eq "" -or $linha.StartsWith("#")) {
        return
    }
    $chave, $valor = $linha.Split("=", 2)
    [System.Environment]::SetEnvironmentVariable($chave.Trim(), $valor.Trim(), "Process")
}

Push-Location $raizProjeto
try {
    Write-Host "Ingerindo aulas de $Origem na coleção '$Colecao' do Qdrant..."
    uv run python scripts/ingest.py --origem $Origem --colecao $Colecao
}
finally {
    Pop-Location
}
