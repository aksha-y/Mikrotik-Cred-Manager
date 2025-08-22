from fastapi import FastAPI, Request, Form, Depends, HTTPException, status, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
import logging
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Import our modules
from database import init_database, db
from auth import SessionManager, UserManager, generate_temp_password
from mikrotik_manager import MikroTikManager

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

# Initialize FastAPI app
app = FastAPI(
    title="Mikrotik-Manager",
    description="Secure web platform for MikroTik device management (credentials, syslog, and more)",
    version="1.0.0"
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Security / cookies config (False in local dev, True in production HTTPS)
SECURE_COOKIES = os.getenv('SECURE_COOKIES', 'false').lower() == 'true'

# Initialize managers
session_manager = SessionManager(db)
user_manager = UserManager(db)
mikrotik_manager = MikroTikManager()

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    try:
        init_database()
        logging.info("Database initialized successfully on startup")
    except Exception as e:
        logging.error(f"Database initialization failed: {e}")

# Dependency to get current user
async def get_current_user(request: Request, session_token: str = Cookie(None)):
    if not session_token:
        return None
    
    user_data = session_manager.validate_session(session_token)
    if not user_data:
        return None
    
    return user_data

# Dependency to require authentication
async def require_auth(current_user = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return current_user

# Dependency to require admin role
async def require_admin(current_user = Depends(require_auth)):
    if current_user['role'] != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

# Helper function to log activity
def log_activity(user_id: int, action: str, target_ip: str = None, details: str = None, 
                ip_address: str = None, user_agent: str = None, status: str = 'success', target_identity: str = None):
    try:
        query = """
            INSERT INTO activity_logs (user_id, action, target_ip, target_identity, details, ip_address, user_agent, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        db.execute_query(query, (user_id, action, target_ip, target_identity, details, ip_address, user_agent, status))
    except Exception as e:
        logging.error(f"Error logging activity: {e}")

# Routes

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, current_user = Depends(get_current_user)):
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    # Mark any expired credential requests as expired before showing dashboard
    try:
        db.execute_query("UPDATE credential_requests SET status='expired' WHERE status='active' AND expires_at <= NOW()")
    except Exception as _e:
        logging.warning(f"Failed to auto-expire requests: {_e}")

    # Get recent activity for dashboard
    recent_requests_query = """
        SELECT cr.*, u.username, u.full_name 
        FROM credential_requests cr
        JOIN users u ON cr.user_id = u.id
        WHERE (cr.user_id = %s) OR (%s = 'admin')
        ORDER BY cr.created_at DESC
        LIMIT 10
    """
    
    recent_requests = db.execute_query(recent_requests_query, (
        current_user['id'], 
        current_user['role']
    ))
    
    # Get statistics
    stats_query = """
        SELECT 
            COUNT(*) as total_requests,
            COUNT(CASE WHEN status = 'active' THEN 1 END) as active_requests,
            COUNT(CASE WHEN status = 'expired' THEN 1 END) as expired_requests,
            COUNT(CASE WHEN created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR) THEN 1 END) as today_requests
        FROM credential_requests
        WHERE (user_id = %s) OR (%s = 'admin')
    """
    
    stats = db.execute_query(stats_query, (current_user['id'], current_user['role']))
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": current_user,
        "recent_requests": recent_requests or [],
        "stats": stats[0] if stats else {}
    })

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    # Get client info
    client_ip = request.client.host
    user_agent = request.headers.get("user-agent", "")
    
    # Authenticate user
    user = user_manager.authenticate_user(username, password)
    
    if not user:
        log_activity(None, "login_failed", details=f"Failed login attempt for username: {username}", 
                    ip_address=client_ip, user_agent=user_agent, status='failed')
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Invalid username or password"
        })
    
    # Create session
    session_token = session_manager.create_session(user['id'], client_ip, user_agent)
    
    if not session_token:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Failed to create session"
        })
    
    # Log successful login
    log_activity(user['id'], "login_success", ip_address=client_ip, user_agent=user_agent)
    
    # Create response with session cookie
    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(
        key="session_token",
        value=session_token,
        max_age=1800,  # 30 minutes
        httponly=True,
        secure=SECURE_COOKIES,  # True in production with HTTPS, False for local
        samesite="lax"
    )
    
    return response

@app.post("/logout")
async def logout(request: Request, current_user = Depends(require_auth), session_token: str = Cookie(None)):
    if session_token:
        session_manager.invalidate_session(session_token)
    
    log_activity(current_user['id'], "logout", ip_address=request.client.host)
    
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("session_token")
    return response

@app.get("/request-credentials", response_class=HTMLResponse)
async def request_credentials_page(request: Request, current_user = Depends(require_auth)):
    return templates.TemplateResponse("request_credentials.html", {
        "request": request,
        "user": current_user
    })

# API endpoints used by the Request Credentials page
@app.get("/api/test-connection/{ip}", response_class=JSONResponse)
async def api_test_connection(ip: str, current_user = Depends(require_auth)):
    try:
        res = mikrotik_manager.test_connection(ip)
        return JSONResponse(res)
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

@app.get("/api/device-info/{ip}", response_class=JSONResponse)
async def api_device_info(ip: str, current_user = Depends(require_auth)):
    try:
        res = mikrotik_manager.get_device_info(ip)
        return JSONResponse(res)
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

@app.post("/request-credentials")
async def request_credentials(
    request: Request,
    wan_ip: str = Form(...),
    purpose: str = Form(...),
    current_user = Depends(require_auth)
):
    # Use admin-configured per-user duration exactly (no user override)
    duration = int(current_user.get('allowed_duration_minutes') or 30)

    # Test connection first
    connection_test = mikrotik_manager.test_connection(wan_ip)
    if not connection_test['success']:
        log_activity(current_user['id'], "credential_request_failed", wan_ip, 
                    f"Connection test failed: {connection_test['error']}", 
                    request.client.host, status='failed')
        
        return templates.TemplateResponse("request_credentials.html", {
            "request": request,
            "user": current_user,
            "error": f"Cannot connect to device: {connection_test['error']}"
        })
    else:
        # Enrich success path with identity in logs
        ident = connection_test.get('identity')
        if ident:
            log_activity(current_user['id'], "connection_test_success", wan_ip, 
                        f"Identity: {ident}", request.client.host, target_identity=ident)
    
    # Create temporary user with username prefix and mapped MikroTik group
    username_prefix = f"{current_user['username']}-"
    group = mikrotik_manager.map_role_to_group(current_user['role'])
    result = mikrotik_manager.create_temporary_user(
        wan_ip,
        duration,
        username_prefix=username_prefix,
        group=group,
    )
    
    if not result['success']:
        log_activity(current_user['id'], "credential_request_failed", wan_ip, 
                    f"Failed to create temp user: {result['error']}", 
                    request.client.host, status='failed')
        
        return templates.TemplateResponse("request_credentials.html", {
            "request": request,
            "user": current_user,
            "error": f"Failed to create credentials: {result['error']}"
        })
    
    # Fetch identity for logging and persistence (prefer result from creation when it used temp creds)
    device_identity = result.get('device_identity')
    if not device_identity:
        identity_info = mikrotik_manager.test_connection(wan_ip)
        device_identity = identity_info.get('identity') if identity_info.get('success') else None
    
    # Store request in database
    expires_at = datetime.now() + timedelta(minutes=duration)
    insert_query = """
        INSERT INTO credential_requests (user_id, wan_ip, device_identity, purpose, duration_minutes, 
                                       temp_username, temp_password, expires_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    try:
        db.execute_query(insert_query, (
            current_user['id'], wan_ip, device_identity, purpose, duration,
            result['username'], result['password'], expires_at
        ))
        
        ident_detail = f" [{device_identity}]" if device_identity else ""
        log_activity(current_user['id'], "credential_request_success", wan_ip, 
                    f"Created temp user: {result['username']} for {duration} minutes{ident_detail}", 
                    request.client.host, target_identity=device_identity)
        
        return templates.TemplateResponse("credentials_success.html", {
            "request": request,
            "user": current_user,
            "credentials": result,
            "wan_ip": wan_ip,
            "device_identity": device_identity,
            "purpose": purpose,
            "duration": duration
        })
        
    except Exception as e:
        logging.error(f"Error storing credential request: {e}")
        # Try to revoke the created user since we couldn't store the request
        try:
            mikrotik_manager.revoke_temporary_user(wan_ip, result['username'])
        except Exception as revoke_err:
            logging.warning(f"Rollback revoke failed: {revoke_err}")
        
        return templates.TemplateResponse("request_credentials.html", {
            "request": request,
            "user": current_user,
            "error": f"Failed to store request in database: {e}"
        })

@app.get("/my-requests", response_class=HTMLResponse)
async def my_requests(request: Request, current_user = Depends(require_auth)):
    # Mark user's expired requests
    try:
        db.execute_query("UPDATE credential_requests SET status='expired' WHERE status='active' AND expires_at <= NOW() AND user_id=%s", (current_user['id'],))
    except Exception as _e:
        logging.warning(f"Failed to auto-expire user requests: {_e}")

    query = """
        SELECT * FROM credential_requests 
        WHERE user_id = %s 
        ORDER BY created_at DESC
    """
    
    requests = db.execute_query(query, (current_user['id'],))
    
    return templates.TemplateResponse("my_requests.html", {
        "request": request,
        "user": current_user,
        "requests": requests or []
    })

@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, current_user = Depends(require_auth)):
    # Load user record to ensure fresh data
    user_query = "SELECT id, username, email, full_name, role, is_active, created_at FROM users WHERE id = %s"
    users = db.execute_query(user_query, (current_user['id'],))
    user = users[0] if users else current_user
    return templates.TemplateResponse("profile.html", {
        "request": request,
        "user": user
    })

@app.post("/revoke-credentials/{request_id}")
async def revoke_credentials(request_id: int, request: Request, current_user = Depends(require_auth)):
    # Get the credential request
    query = "SELECT * FROM credential_requests WHERE id = %s AND user_id = %s AND status = 'active'"
    cred_request = db.execute_query(query, (request_id, current_user['id']))
    
    if not cred_request:
        raise HTTPException(status_code=404, detail="Request not found or already revoked")
    
    cred_request = cred_request[0]
    
    # Revoke on MikroTik device
    result = mikrotik_manager.revoke_temporary_user(cred_request['wan_ip'], cred_request['temp_username'])
    
    # Update database
    update_query = "UPDATE credential_requests SET status = 'revoked', revoked_at = NOW() WHERE id = %s"
    db.execute_query(update_query, (request_id,))
    
    ident_detail = f" [{cred_request.get('device_identity')}]" if cred_request.get('device_identity') else ""
    log_activity(current_user['id'], "credential_revoked", cred_request['wan_ip'], 
                f"Revoked temp user: {cred_request['temp_username']}{ident_detail}", request.client.host, target_identity=cred_request.get('device_identity'))
    
    return JSONResponse({"success": True, "message": "Credentials revoked successfully"})

# Debug: fetch raw identity info
@app.get("/admin/identity-debug", response_class=JSONResponse)
async def identity_debug(ip: str, current_user = Depends(require_admin)):
    try:
        data = mikrotik_manager.fetch_identity_debug(ip)
        return JSONResponse(content=data)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

# Admin routes
@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request, current_user = Depends(require_admin)):
    # Refresh statuses to keep widgets accurate
    try:
        db.execute_query("UPDATE credential_requests SET status='expired' WHERE status='active' AND expires_at <= NOW()")
    except Exception as _e:
        logging.warning(f"auto-expire (admin dashboard): {_e}")

    # Get statistics
    stats_query = """
        SELECT 
            (SELECT COUNT(*) FROM users WHERE is_active = TRUE) as total_users,
            (SELECT COUNT(*) FROM credential_requests) as total_requests,
            (SELECT COUNT(*) FROM credential_requests WHERE status = 'active') as active_requests,
            (SELECT COUNT(*) FROM activity_logs WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)) as today_activities
    """
    
    stats_rows = db.execute_query(stats_query) or [{"total_users":0,"total_requests":0,"active_requests":0,"today_activities":0}]
    stats = stats_rows[0]

    # Pull recent system activity (latest 10)
    recent_query = """
        SELECT al.*, u.username, u.full_name
        FROM activity_logs al
        LEFT JOIN users u ON al.user_id = u.id
        ORDER BY al.created_at DESC
        LIMIT 10
    """
    recent_logs = db.execute_query(recent_query) or []
    
    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "user": current_user,
        "stats": stats,
        "recent_logs": recent_logs
    })

@app.get("/admin/users", response_class=HTMLResponse)
async def admin_users(request: Request, current_user = Depends(require_admin)):
    users = user_manager.get_all_users()
    
    return templates.TemplateResponse("admin/users.html", {
        "request": request,
        "user": current_user,
        "users": users
    })

@app.post("/admin/users/create")
async def create_user(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    full_name: str = Form(...),
    role: str = Form(...),
    password: str = Form(...),
    allowed_duration_minutes: str = Form(""),
    current_user = Depends(require_admin)
):
    # Only admin can set per-user allowed_duration_minutes
    allowed_val = None
    if allowed_duration_minutes != "":
        try:
            allowed_val = int(allowed_duration_minutes)
        except Exception:
            users = user_manager.get_all_users()
            return templates.TemplateResponse("admin/users.html", {
                "request": request,
                "user": current_user,
                "users": users,
                "error": "Invalid Max Allowed Duration"
            })
    success = user_manager.create_user(username, email, password, full_name, role, allowed_duration_minutes=allowed_val if allowed_val is not None else 30)
    
    if success:
        log_activity(current_user['id'], "user_created", details=f"Created user: {username}")
        return RedirectResponse(url="/admin/users", status_code=302)
    else:
        users = user_manager.get_all_users()
        return templates.TemplateResponse("admin/users.html", {
            "request": request,
            "user": current_user,
            "users": users,
            "error": "Failed to create user"
        })

@app.post("/admin/users/{user_id}/delete")
async def delete_user(user_id: int, current_user = Depends(require_admin)):
    if user_id == current_user['id']:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    success = user_manager.delete_user(user_id)
    
    if success:
        log_activity(current_user['id'], "user_deleted", details=f"Deleted user ID: {user_id}")
    
    return JSONResponse({"success": success})

@app.post("/admin/users/{user_id}/update")
async def update_user(user_id: int, request: Request, current_user = Depends(require_admin)):
    try:
        data = await request.json()
    except Exception:
        data = {}
    # Only allow specific fields
    allowed = {k: data[k] for k in ["email", "full_name", "role", "is_active", "allowed_duration_minutes"] if k in data}
    if "is_active" in allowed:
        allowed["is_active"] = bool(allowed["is_active"])  # coerce to bool
    if "allowed_duration_minutes" in allowed:
        try:
            allowed["allowed_duration_minutes"] = int(allowed["allowed_duration_minutes"]) if allowed["allowed_duration_minutes"] is not None else None
        except Exception:
            return JSONResponse({"success": False, "error": "Invalid allowed_duration_minutes"}, status_code=400)
    if not allowed:
        return JSONResponse({"success": False, "error": "No valid fields provided"}, status_code=400)
    # Optional password change
    new_password = data.get("new_password")
    if new_password:
        if not user_manager.change_password(user_id, new_password):
            return JSONResponse({"success": False, "error": "Failed to change password"}, status_code=500)
    
    success = user_manager.update_user(user_id, **allowed)
    if success or new_password:
        changed = ", ".join([f"{k}={allowed[k]}" for k in allowed.keys()])
        if new_password:
            changed = (changed + ", password=***") if changed else "password=***"
        log_activity(current_user['id'], "user_updated", details=f"Updated user ID {user_id}: {changed}")
    return JSONResponse({"success": bool(success or new_password)})

@app.get("/admin/logs", response_class=HTMLResponse)
async def admin_logs(
    request: Request,
    current_user = Depends(require_admin),
    page: int = 1,
    action: str = "",
    status: str = "",
    user: str = "",      # username or full name
    ip: str = "",
    date: str = "",      # today|yesterday|week|month|"" (all)
    details: str = ""
):
    # Pagination
    if page < 1:
        page = 1
    page_size = 50
    offset = (page - 1) * page_size

    # Build filters
    filters = []
    params = []

    if action:
        filters.append("al.action = %s")
        params.append(action)

    if status:
        filters.append("al.status = %s")
        params.append(status)

    if user:
        filters.append("(LOWER(u.username) LIKE %s OR LOWER(u.full_name) LIKE %s)")
        like = f"%{user.lower()}%"
        params.extend([like, like])

    if ip:
        filters.append("al.ip_address LIKE %s")
        params.append(f"%{ip}%")

    if details:
        filters.append("LOWER(al.details) LIKE %s")
        params.append(f"%{details.lower()}%")

    if date:
        if date == "today":
            filters.append("DATE(al.created_at) = CURDATE()")
        elif date == "yesterday":
            filters.append("DATE(al.created_at) = DATE_SUB(CURDATE(), INTERVAL 1 DAY)")
        elif date == "week":
            filters.append("al.created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)")
        elif date == "month":
            filters.append("al.created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)")

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

    # Counts on filtered set
    counts_query = f"""
        SELECT
            COUNT(*) AS total_matching,
            COUNT(CASE WHEN al.status = 'success' THEN 1 END) AS success_count,
            COUNT(CASE WHEN al.status = 'failed' THEN 1 END) AS failed_count
        FROM activity_logs al
        LEFT JOIN users u ON al.user_id = u.id
        {where_clause}
    """
    counts = db.execute_query(counts_query, tuple(params)) or [{
        "total_matching": 0,
        "success_count": 0,
        "failed_count": 0
    }]
    total_matching = counts[0]["total_matching"] or 0
    success_count = counts[0]["success_count"] or 0
    failed_count = counts[0]["failed_count"] or 0

    total_pages = (total_matching + page_size - 1) // page_size if total_matching else 1

    # Fetch filtered page
    logs_query = f"""
        SELECT al.*, u.username, u.full_name
        FROM activity_logs al
        LEFT JOIN users u ON al.user_id = u.id
        {where_clause}
        ORDER BY al.created_at DESC
        LIMIT %s OFFSET %s
    """
    logs_params = tuple(params + [page_size, offset])
    logs = db.execute_query(logs_query, logs_params) or []

    # Last 24h count (global)
    count_24h_query = """
        SELECT COUNT(*) AS cnt
        FROM activity_logs
        WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
    """
    recent_24h = db.execute_query(count_24h_query)
    last_24h_count = (recent_24h[0]["cnt"] if recent_24h else 0)

    # Support quick group filter from menu
    group = request.query_params.get("group")
    if group == "mikrotik" and not action:
        action = None  # leave server results; UI will suggest group
    
    # Load syslog URL for UI links
    syslog_url = os.getenv("SYSLOG_UI_URL", "")

    return templates.TemplateResponse("admin/logs.html", {
        "request": request,
        "user": current_user,
        "logs": logs,
        "last_24h_count": last_24h_count,
        # Pagination
        "page": page,
        "total_pages": total_pages,
        # Filtered totals
        "total_matching": total_matching,
        "success_count": success_count,
        "failed_count": failed_count,
        # Echo filters
        "f_action": action,
        "f_status": status,
        "f_user": user,
        "f_ip": ip,
        "f_date": date,
        "f_details": details,
        # Extras
        "syslog_url": syslog_url,
    })

@app.get("/admin/requests", response_class=HTMLResponse)
async def admin_requests(request: Request, current_user = Depends(require_admin)):
    # Mark any expired requests globally
    try:
        db.execute_query("UPDATE credential_requests SET status='expired' WHERE status='active' AND expires_at <= NOW()")
    except Exception as _e:
        logging.warning(f"Failed to auto-expire requests (admin): {_e}")

    query = """
        SELECT cr.*, u.username, u.full_name
        FROM credential_requests cr
        JOIN users u ON cr.user_id = u.id
        ORDER BY cr.created_at DESC
        LIMIT 100
    """
    
    requests = db.execute_query(query)
    
    return templates.TemplateResponse("admin/requests.html", {
        "request": request,
        "user": current_user,
        "requests": requests or []
    })

@app.get("/admin/settings", response_class=HTMLResponse)
async def admin_settings(request: Request, current_user = Depends(require_admin)):
    return templates.TemplateResponse("admin/settings.html", {
        "request": request,
        "user": current_user,
        "service_user": mikrotik_manager.service_user,
        "api_port": mikrotik_manager.api_port,
        "use_tls": mikrotik_manager.use_tls,
    })



def update_env_file(updates: dict):
    """Update or append keys in the .env file. Returns (success: bool, error: str)."""
    try:
        env_path = ".env"
        lines = []
        existing = {}
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            for i, line in enumerate(lines):
                if line.strip().startswith("#") or "=" not in line:
                    continue
                key = line.split("=", 1)[0].strip()
                existing[key] = i
        else:
            lines = []
        for key, value in updates.items():
            new_line = f"{key}={value}\n"
            if key in existing:
                lines[existing[key]] = new_line
            else:
                lines.append(new_line)
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        return True, ""
    except Exception as e:
        return False, str(e)

@app.post("/admin/settings/update")
async def update_settings(
    request: Request,
    service_user: str = Form(...),
    service_pass: str = Form(...),
    api_port: int = Form(8728),
    use_tls: str = Form("auto"),  # on|off|auto
    persist_env: str = Form("off"),
    current_user = Depends(require_admin)
):
    # Update in-memory manager values
    mikrotik_manager.service_user = service_user
    mikrotik_manager.service_pass = service_pass
    try:
        mikrotik_manager.api_port = int(api_port)
    except Exception:
        mikrotik_manager.api_port = 8728

    # TLS flag handling
    if use_tls in ("on", "off"):
        mikrotik_manager.use_tls = (use_tls == "on")
    else:
        # auto heuristic
        mikrotik_manager.use_tls = (mikrotik_manager.api_port == 8729)

    message = "Service settings updated for current session."
    persist_success = True

    if persist_env == "on":
        ok, err = update_env_file({
            "MIKROTIK_SERVICE_USER": service_user,
            "MIKROTIK_SERVICE_PASS": service_pass,
            "MIKROTIK_API_PORT": str(mikrotik_manager.api_port),
            "MIKROTIK_API_TLS": ("true" if mikrotik_manager.use_tls else "false")
        })
        if ok:
            # Also write canonical env var name for consistency
            ok2, err2 = update_env_file({
                "MIKROTIK_SERVICE_PASSWORD": service_pass
            })
            if ok2:
                message = "Service settings updated and saved to .env."
            else:
                message = "Service settings saved, but failed to write canonical password key."
        else:
            persist_success = False
            message += f" Failed to update .env: {err}"

    # Log the change without exposing secrets
    log_activity(current_user['id'], "settings_updated", details="Updated MikroTik service settings")

    return templates.TemplateResponse("admin/settings.html", {
        "request": request,
        "user": current_user,
        "service_user": mikrotik_manager.service_user,
        "api_port": mikrotik_manager.api_port,
        "use_tls": mikrotik_manager.use_tls,
        "message": message,
        "persist_success": persist_success
    })

# Admin maintenance endpoints
@app.post("/admin/cleanup-sessions")
async def cleanup_sessions(current_user = Depends(require_admin)):
    """Remove expired and inactive sessions from the database."""
    try:
        deleted = db.execute_query("DELETE FROM sessions WHERE expires_at <= NOW() OR is_active = FALSE") or 0
        try:
            log_activity(current_user['id'], "cleanup_sessions", details=f"Deleted {deleted} expired/inactive sessions")
        except Exception:
            pass
        return JSONResponse({"success": True, "deleted": int(deleted)})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

@app.post("/admin/requests/cleanup-expired")
async def cleanup_expired_requests(current_user = Depends(require_admin)):
    """Revoke all expired credential requests on devices and mark them revoked."""
    try:
        # First mark any overdue active requests as expired
        db.execute_query("UPDATE credential_requests SET status='expired' WHERE status='active' AND expires_at <= NOW()")
        rows = db.execute_query("""
            SELECT id, wan_ip, temp_username
            FROM credential_requests
            WHERE status='expired'
        """) or []
        revoked = 0
        errors = 0
        for r in rows:
            res = mikrotik_manager.revoke_temporary_user(r['wan_ip'], r['temp_username'])
            if res and res.get('success'):
                db.execute_query("UPDATE credential_requests SET status='revoked', revoked_at = NOW() WHERE id = %s", (r['id'],))
                revoked += 1
            else:
                errors += 1
        try:
            log_activity(current_user['id'], "cleanup_expired_requests", details=f"Revoked {revoked} expired credentials; errors={errors}")
        except Exception:
            pass
        return JSONResponse({"success": True, "revoked": revoked, "errors": errors})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

# API endpoints for AJAX calls
@app.get("/api/device-info/{ip_address}")
async def get_device_info(ip_address: str, current_user = Depends(require_auth)):
    result = mikrotik_manager.get_device_info(ip_address)
    return JSONResponse(result)

@app.get("/api/test-connection/{ip_address}")
async def test_connection(ip_address: str, current_user = Depends(require_auth)):
    result = mikrotik_manager.test_connection(ip_address)
    return JSONResponse(result)

# Uptime endpoint
PROCESS_START = datetime.now()

def _humanize_uptime(seconds: int) -> str:
    minutes, sec = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    parts = []
    if days: parts.append(f"{days}d")
    if hours: parts.append(f"{hours}h")
    if minutes: parts.append(f"{minutes}m")
    parts.append(f"{sec}s")
    return ' '.join(parts)

@app.get("/api/uptime")
async def api_uptime():
    seconds = (datetime.now() - PROCESS_START).total_seconds()
    return JSONResponse({
        "seconds": int(seconds),
        "human": _humanize_uptime(seconds)
    })

@app.get("/api/system-load")
async def api_system_load():
    """Return a simple system load approximation for Windows.
    We approximate CPU usage over a short sleep to avoid extra deps.
    """
    try:
        import time, psutil  # if psutil is available, use it
        cpu = psutil.cpu_percent(interval=0.3)
        return JSONResponse({"load_percent": cpu})
    except Exception:
        try:
            # Fallback: crude time-based pseudo-load (not accurate, but avoids crash)
            start = time.perf_counter()
            # Busy-wait a bit to measure performance (very light)
            for _ in range(1000000):
                pass
            elapsed = time.perf_counter() - start
            # Map elapsed to a 0-100 range (device-dependent)
            # Tune: faster CPUs -> smaller elapsed -> lower load
            # We'll invert: load% ~ min(100, max(0, k/elapsed)) with k chosen empirically
            k = 0.02
            approx = max(0.0, min(100.0, (k / max(elapsed, 1e-6)) * 100.0))
            return JSONResponse({"load_percent": approx})
        except Exception:
            return JSONResponse({"load_percent": 0})

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    if not init_database():
        logging.error("Failed to initialize database")
        exit(1)
    
    logging.info("MikroTik Credential Manager started successfully")

# Run the application
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )