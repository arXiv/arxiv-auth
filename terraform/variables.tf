variable "gcp_project_id" {
  description = "GCP Project ID corresponding to environment"
  type        = string
}

variable "gcp_region" {
  description = "GCP Region for resource deployments"
  type        = string
}

variable "env" {
  description = "Deployment environment - DEV or PROD"
  type        = string
}

variable "image_path" {
  description = "Path to the container image in Artifact Registry"
  type        = string
}

variable "classic_db_secret_name" {
  description = "Name of the secret containing the classic database URI"
  type        = string
}

variable "jwt_secret_name" {
  description = "Name of the secret containing the JWT secret"
  type        = string
}

variable "classic_session_hash_secret_name" {
  description = "Name of the secret containing the classic session hash"
  type        = string
}

variable "cloud_sql_instance_name" {
  description = "Name of the Cloud SQL instance"
  type        = string
}
