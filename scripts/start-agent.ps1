<#
.SYNOPSIS
    Lê os segredos de secrets.txt, exporta como variáveis de ambiente e sobe o
    servidor do agente Mentor (FastAPI/uvicorn).

.EXAMPLE
    .\scripts\start-agent.ps1
    .\scripts\start-agent.ps1 -SecretsFile .\secrets.txt -Port 8000 -Reload
#>

param(
    [string]$SecretsFile = (Join-Path $PSScriptRoot "..\secrets.txt"),
    [int]$Port = 8000,
    [switch]$Reload
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
    $args = @(
        "run", "uvicorn", "agent.api:app",
        "--host", "0.0.0.0",
        "--port", "$Port",
        # Rede de segurança: força o encerramento mesmo se alguma conexão SSE
        # ou chamada ao runtime do agente travar o shutdown gracioso.
        "--timeout-graceful-shutdown", "5"
    )
    if ($Reload) {
        $args += "--reload"
    }
    Write-Host "Iniciando o agente na porta $Port..."
    & uv @args
}
finally {
    Pop-Location
}
