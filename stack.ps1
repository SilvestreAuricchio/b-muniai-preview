param(
    [Parameter(Position = 0)]
    [ValidateSet("up","down","restart","build","logs","clean","nuke")]
    [string]$Command = "up",

    [Parameter(Position = 1)]
    [string]$Service = ""
)

switch ($Command) {

    "up" {
        docker compose up --build -d
    }

    "down" {
        docker compose down
    }

    "restart" {
        docker compose down
        docker compose up --build -d
    }

    "build" {
        docker compose build
    }

    "logs" {
        if ($Service) {
            docker compose logs -f $Service
        } else {
            docker compose logs -f
        }
    }

    "clean" {
        Write-Host "Removing containers and named volumes (redis/rabbitmq/grafana/certs)..."
        Write-Host "Bind-mount data in ./data/ is NOT removed."
        docker compose down -v
    }

    "nuke" {
        Write-Warning "This will destroy ALL data: named volumes AND ./data/ directories."
        $confirm = Read-Host "Type YES to confirm"
        if ($confirm -ne "YES") {
            Write-Host "Aborted."
            exit 0
        }
        docker compose down -v
        $dirs = @("data\postgres", "data\mongodb", "data\prometheus")
        foreach ($dir in $dirs) {
            if (Test-Path $dir) {
                Remove-Item -Recurse -Force $dir
                Write-Host "Removed $dir"
            }
        }
        Write-Host "Done."
    }
}
