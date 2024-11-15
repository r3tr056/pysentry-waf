import psutil


def check_memory_usage():
    memory = psutil.virtual_memory()
    status = "ok" if memory.percent < 85 else "warning" if memory.percent < 95 else "error"
    return {
        "status": status,
        "total_memory_mb": memory.total // (1024 * 1024),
        "used_memory_mb": memory.used // (1024 * 1024),
        "usage_percent": memory.percent,
        "message": "Memory usage is within limits" if status == "ok" else "High memory usage detected"
    }

def check_disk_space():
    disk = psutil.disk_usage('/')
    status = "ok" if disk.percent < 85 else "warning" if disk.percent < 95 else "error"
    return {
        "status": status,
        "total_disk_space_mb": disk.total // (1024 * 1024),
        "used_disk_space_mb": disk.used // (1024 * 1024),
        "usage_percent": disk.percent,
        "message": "Disk space is sufficient" if status == "ok" else "Low disk space warning"
    }