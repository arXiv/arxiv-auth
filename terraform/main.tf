terraform {
  required_version = "~> 1.13"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 7.2"
    }
  }
  backend "gcs" {
    prefix = "activity-dashboard-api"
  }
}

provider "google" {
  project = var.gcp_project_id # default inherited by all resources
  region  = var.gcp_region     # default inherited by all resources
}

# Allow public access (disable google auth)
# resource "google_cloud_run_v2_service_iam_member" "all_users_invoker" {
#   location = var.gcp_region
#   name     = "login-app"
#   role     = "roles/run.invoker"
#   member   = "allUsers"
# }

resource "google_cloud_run_service_iam_binding" "default" {
  location = var.gcp_region
  service  = google_cloud_run_v2_service.login-app.name
  role     = "roles/run.invoker"
  members = [
    "allUsers"
  ]
}

### service account ###

resource "google_service_account" "account" {
  account_id = "login-app"
  description = "Service account to deploy login app cloud run instance"
}

resource "google_project_iam_member" "cloud_sql_client_role" {
  project = var.gcp_project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.account.email}"
}

resource "google_secret_manager_secret_iam_member" "classic_db_secret_accessor" {
  secret_id = var.classic_db_secret_name
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.account.email}"
  lifecycle {
    ignore_changes = [secret_id]
  }
}

resource "google_secret_manager_secret_iam_member" "jwt_secret_accessor" {
  secret_id = var.jwt_secret_name
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.account.email}"

  lifecycle {
    ignore_changes = [secret_id]
  }
}

resource "google_secret_manager_secret_iam_member" "classic_session_hash_secret_accessor" {
  secret_id = var.classic_session_hash_secret_name
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.account.email}"
  lifecycle {
    ignore_changes = [secret_id]
  }
}

resource "google_project_iam_member" "cloud_run_admin" {
  project = var.gcp_project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${google_service_account.account.email}"
}

resource "google_project_iam_member" "logs_writer" {
  project = var.gcp_project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.account.email}"
}

resource "google_project_iam_member" "service_account_user" {
  project = var.gcp_project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${google_service_account.account.email}"
}

### cloud run instance ###

resource "google_cloud_run_v2_service" "login_app" {
  name     = "login_app"
  location = var.gcp_region

  deletion_protection = false

  ingress = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.account.email
    containers {
      image = var.image_path

      ports {
        name           = "http1"
        container_port = 8000
      }

      startup_probe {
        timeout_seconds   = 240
        period_seconds    = 240
        failure_threshold = 1
        tcp_socket {
          port = 8000
        }
      }

      resources {
        startup_cpu_boost = true
      }

      env {
        name  = "ENV"
        value = var.env
      }
      env {
        name = "REDIS_FAKE"
        value = 1
      }

      env {
        name = "BASE_SERVER"
        value = var.base_server
      }
      env {
        name = "MAIN_SERVER"
        value = var.main_server
      }
      env {
        name = "HELP_SERVER"
        value = var.help_server
      }

      env {
        name = "CLASSIC_DATABASE_URI"
        value_source {
          secret_key_ref {
            secret  = var.classic_db_secret_name
            version = "latest"
          }
        }
      }
      env {
        name = "JWT_SECRET"
        value_source {
          secret_key_ref {
            secret  = var.jwt_secret_name
            version = "latest"
          }
        }
      }
      env {
        name = "CLASSIC_SESSION_HASH"
        value_source {
          secret_key_ref {
            secret  = var.classic_session_hash_secret_name
            version = "latest"
          }
        }
      }

      volume_mounts {
        mount_path = "/cloudsql"
        name       = "cloudsql"
      }
    }

    volumes {
      name = "cloudsql"
      cloud_sql_instance {
        instances = [
          "${var.gcp_project_id}:${var.gcp_region}:${var.cloud_sql_instance_name}",
        ]
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
}
