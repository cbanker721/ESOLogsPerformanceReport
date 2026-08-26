$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$configPath = Join-Path $repoRoot 'config.local.js'
$kbDir = Join-Path $repoRoot 'knowledge-base\graphql'

if (-not (Test-Path $configPath)) {
  throw "Missing config file: $configPath"
}

$configText = Get-Content $configPath -Raw

function Get-ConfigValue([string]$name) {
  $pattern = '{0}\s*:\s*"([^"]+)"' -f [regex]::Escape($name)
  $match = [regex]::Match($configText, $pattern)
  if ($match.Success) {
    return $match.Groups[1].Value
  }

  return ''
}

$accessToken = Get-ConfigValue 'accessToken'
$apiUrl = Get-ConfigValue 'apiUrl'
$tokenType = Get-ConfigValue 'tokenType'

if ([string]::IsNullOrWhiteSpace($apiUrl)) {
  $apiUrl = 'https://www.esologs.com/api/v2/client'
}

if ([string]::IsNullOrWhiteSpace($tokenType)) {
  $tokenType = 'Bearer'
}

if ([string]::IsNullOrWhiteSpace($accessToken) -or $accessToken -in @('REPLACE_WITH_ACCESS_TOKEN', 'YOUR_ACCESS_TOKEN')) {
  throw "config.local.js accessToken is missing. Set a valid token before running this script."
}

$headers = @{ Authorization = "$tokenType $accessToken" }

New-Item -ItemType Directory -Force -Path $kbDir | Out-Null

$fullQuery = @'
query IntrospectionQuery {
  __schema {
    queryType { name }
    mutationType { name }
    subscriptionType { name }
    types {
      kind
      name
      description
      fields(includeDeprecated: true) {
        name
        description
        args {
          name
          description
          defaultValue
          type {
            kind
            name
            ofType {
              kind
              name
              ofType {
                kind
                name
                ofType {
                  kind
                  name
                }
              }
            }
          }
        }
        type {
          kind
          name
          ofType {
            kind
            name
            ofType {
              kind
              name
              ofType {
                kind
                name
              }
            }
          }
        }
        isDeprecated
        deprecationReason
      }
      inputFields {
        name
        description
        defaultValue
        type {
          kind
          name
          ofType {
            kind
            name
            ofType {
              kind
              name
              ofType {
                kind
                name
              }
            }
          }
        }
      }
      interfaces {
        kind
        name
      }
      enumValues(includeDeprecated: true) {
        name
        description
        isDeprecated
        deprecationReason
      }
      possibleTypes {
        kind
        name
      }
    }
    directives {
      name
      description
      locations
      args {
        name
        description
        defaultValue
        type {
          kind
          name
          ofType {
            kind
            name
            ofType {
              kind
              name
            }
          }
        }
      }
    }
  }
}
'@

$rootQuery = '{ __schema { queryType { name fields { name description args { name description defaultValue type { kind name ofType { kind name ofType { kind name } } } } type { kind name ofType { kind name ofType { kind name } } } } } mutationType { name fields { name description } } subscriptionType { name } directives { name description locations } } }'
$typeQuery = '{ reportData: __type(name: "ReportData") { name description fields { name description args { name description type { kind name ofType { kind name ofType { kind name } } } } type { kind name ofType { kind name ofType { kind name } } } } } characterData: __type(name: "CharacterData") { name description fields { name description args { name description type { kind name ofType { kind name ofType { kind name } } } } type { kind name ofType { kind name ofType { kind name } } } } } guildData: __type(name: "GuildData") { name description fields { name description args { name description type { kind name ofType { kind name ofType { kind name } } } } type { kind name ofType { kind name ofType { kind name } } } } } worldData: __type(name: "WorldData") { name description fields { name description args { name description type { kind name ofType { kind name ofType { kind name } } } } type { kind name ofType { kind name ofType { kind name } } } } } rateLimitData: __type(name: "RateLimitData") { name description fields { name description args { name description type { kind name ofType { kind name ofType { kind name } } } } type { kind name ofType { kind name ofType { kind name } } } } } userData: __type(name: "UserData") { name description fields { name description args { name description type { kind name ofType { kind name ofType { kind name } } } } type { kind name ofType { kind name ofType { kind name } } } } } }'

function Invoke-GraphQL([string]$query) {
  $payload = @{ query = $query; variables = @{} } | ConvertTo-Json -Depth 12
  return Invoke-RestMethod -Method Post -Uri $apiUrl -Headers $headers -Body $payload -ContentType 'application/json'
}

try {
  $fullResult = Invoke-GraphQL $fullQuery
  $rootResult = Invoke-GraphQL $rootQuery
  $typeResult = Invoke-GraphQL $typeQuery
} catch {
  throw "GraphQL request failed. Ensure token is valid and not expired. Details: $($_.Exception.Message)"
}

$fullResult | ConvertTo-Json -Depth 100 | Set-Content (Join-Path $kbDir 'introspection-full.json')
$rootResult | ConvertTo-Json -Depth 40 | Set-Content (Join-Path $kbDir 'root-schema-summary.json')
$typeResult | ConvertTo-Json -Depth 40 | Set-Content (Join-Path $kbDir 'core-types-summary.json')

$types = $fullResult.data.__schema.types
$typeCount = $types.Count
$objectCount = ($types | Where-Object { $_.kind -eq 'OBJECT' }).Count
$inputObjectCount = ($types | Where-Object { $_.kind -eq 'INPUT_OBJECT' }).Count
$enumCount = ($types | Where-Object { $_.kind -eq 'ENUM' }).Count
$scalarCount = ($types | Where-Object { $_.kind -eq 'SCALAR' }).Count
$interfaceCount = ($types | Where-Object { $_.kind -eq 'INTERFACE' }).Count
$unionCount = ($types | Where-Object { $_.kind -eq 'UNION' }).Count
$directiveCount = $fullResult.data.__schema.directives.Count

$rootFieldLines = @()
foreach ($f in $rootResult.data.__schema.queryType.fields) {
  $desc = if ($f.description) { $f.description.Replace("`r`n", ' ').Replace("`n", ' ') } else { 'No description available.' }
  $rootFieldLines += '- ' + $f.name + ': ' + $desc
}

function Format-TypeSection([object]$typeInfo) {
  if (-not $typeInfo) {
    return @('- Type not found.')
  }

  $lines = @()
  $desc = if ($typeInfo.description) { $typeInfo.description.Replace("`r`n", ' ').Replace("`n", ' ') } else { 'No description available.' }
  $lines += '- Description: ' + $desc
  $lines += '- Fields:'
  foreach ($field in $typeInfo.fields) {
    $fieldDesc = if ($field.description) { $field.description.Replace("`r`n", ' ').Replace("`n", ' ') } else { 'No description.' }
    $argSummary = if ($field.args -and $field.args.Count -gt 0) { ($field.args | ForEach-Object { $_.name }) -join ', ' } else { 'none' }
    $lines += '  - ' + $field.name + ' (args: ' + $argSummary + '): ' + $fieldDesc
  }

  return $lines
}

$refreshedAt = Get-Date -Format 'yyyy-MM-dd HH:mm:ss K'

$md = @()
$md += '# ESO Logs GraphQL Knowledge Base'
$md += ''
$md += 'Last refreshed: ' + $refreshedAt
$md += 'Endpoint: ' + $apiUrl
$md += 'Token source: config.local.js accessToken'
$md += ''
$md += '## Schema Overview'
$md += ''
$md += '- Query root type: ' + $rootResult.data.__schema.queryType.name
$md += '- Mutation root type: ' + ($(if ($rootResult.data.__schema.mutationType) { $rootResult.data.__schema.mutationType.name } else { 'none' }))
$md += '- Subscription root type: ' + ($(if ($rootResult.data.__schema.subscriptionType) { $rootResult.data.__schema.subscriptionType.name } else { 'none' }))
$md += '- Total types: ' + $typeCount
$md += '- OBJECT types: ' + $objectCount
$md += '- INPUT_OBJECT types: ' + $inputObjectCount
$md += '- ENUM types: ' + $enumCount
$md += '- SCALAR types: ' + $scalarCount
$md += '- INTERFACE types: ' + $interfaceCount
$md += '- UNION types: ' + $unionCount
$md += '- Directives: ' + $directiveCount
$md += ''
$md += '## Root Query Fields'
$md += ''
$md += $rootFieldLines
$md += ''
$md += '## Core Domain Type Snapshots'
$md += ''
$md += '### ReportData'
$md += (Format-TypeSection $typeResult.data.reportData)
$md += ''
$md += '### CharacterData'
$md += (Format-TypeSection $typeResult.data.characterData)
$md += ''
$md += '### GuildData'
$md += (Format-TypeSection $typeResult.data.guildData)
$md += ''
$md += '### WorldData'
$md += (Format-TypeSection $typeResult.data.worldData)
$md += ''
$md += '### RateLimitData'
$md += (Format-TypeSection $typeResult.data.rateLimitData)
$md += ''
$md += '### UserData'
$md += (Format-TypeSection $typeResult.data.userData)
$md += ''
$md += '## Source Artifacts'
$md += ''
$md += '- introspection-full.json: Full schema introspection result.'
$md += '- root-schema-summary.json: Query root and directives summary.'
$md += '- core-types-summary.json: Focused summary of key top-level data objects.'

$md -join "`r`n" | Set-Content (Join-Path $kbDir 'README.md')

Write-Host "Knowledge base refreshed in $kbDir"
