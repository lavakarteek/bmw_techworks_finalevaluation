variable "aws_region" {
  type        = string
  description = "AWS region for the capstone deployment."
  default     = "us-east-1"
}

variable "temperature_threshold" {
  type        = number
  description = "Temperature in Celsius at which a telemetry event is critical."
  default     = 85
}

variable "critical_fault_codes" {
  type        = string
  description = "Comma-separated fault codes that always create an alert."
  default     = "BATTERY_OVERHEAT,THERMAL_RUNAWAY,COOLING_FAILURE"
}