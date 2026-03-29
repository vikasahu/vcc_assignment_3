output "instance_ip" {
  description = "External IP of the GCP VM"
  value       = google_compute_instance.flask_vm.network_interface[0].access_config[0].nat_ip
}

output "flask_url" {
  description = "URL to access the Flask app on GCP"
  value       = "http://${google_compute_instance.flask_vm.network_interface[0].access_config[0].nat_ip}:5000"
}
