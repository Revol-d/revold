variable "project_name"        { type = string }
variable "environment"         { type = string }
variable "location"            { type = string }
variable "resource_group_name" { type = string }
variable "postgres_subnet_id"  { type = string }

variable "admin_password" {
  type      = string
  sensitive = true
}
