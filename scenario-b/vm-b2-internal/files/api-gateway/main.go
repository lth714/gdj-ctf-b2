// Go API Gateway for 广电网络监控 — internal service
// Contains intentional command injection vulnerability (B-3)
// Build: go build -o api-gateway main.go

package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os/exec"
	"strings"
)

type Response struct {
	Status  string      `json:"status"`
	Message string      `json:"message,omitempty"`
	Data    interface{} `json:"data,omitempty"`
}

type AdminUser struct {
	ID       int    `json:"id"`
	Username string `json:"username"`
	Role     string `json:"role"`
	Token    string `json:"token"`
}

// Hardcoded admin token (used for B-2 SSRF privilege escalation)
var adminToken = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsInJvbGUiOiJhZG1pbiJ9.8f7d3b2a1c4e5f6a7b8c9d0e1f2a3b4c"

func main() {
	http.HandleFunc("/api/health", handleHealth)
	http.HandleFunc("/api/diag", handleDiagnostic)
	http.HandleFunc("/api/admin/token", handleAdminToken)
	http.HandleFunc("/api/admin/users", handleAdminUsers)

	log.Println("API Gateway listening on :8080")
	log.Fatal(http.ListenAndServe("0.0.0.0:8080", nil))
}

func handleHealth(w http.ResponseWriter, r *http.Request) {
	jsonResponse(w, Response{
		Status: "ok",
		Data: map[string]interface{}{
			"service":   "api-gateway",
			"version":   "3.2.1",
			"uptime":    "7d 12h",
			"endpoints": []string{"/api/health", "/api/diag", "/api/admin/token", "/api/admin/users"},
		},
	})
}

func handleDiagnostic(w http.ResponseWriter, r *http.Request) {
	cmd := r.URL.Query().Get("cmd")
	target := r.URL.Query().Get("target")

	if cmd == "" || target == "" {
		jsonError(w, "缺少参数: cmd 和 target (支持: ping, traceroute, nslookup)", 400)
		return
	}

	// Whitelist check... but only checks if cmd STARTS with allowed value
	validCmds := []string{"ping", "traceroute", "nslookup"}
	valid := false
	for _, v := range validCmds {
		if strings.HasPrefix(cmd, v) {
			valid = true
			break
		}
	}

	if !valid {
		jsonError(w, "不支持的命令: "+cmd, 400)
		return
	}

	// VULNERABLE: Command injection via shell execution
	// The target parameter is concatenated directly into shell command
	shellCmd := fmt.Sprintf("%s -c 3 %s 2>&1", cmd, target)
	log.Printf("[DIAG] Executing: %s", shellCmd)

	out, err := exec.Command("sh", "-c", shellCmd).CombinedOutput()
	if err != nil {
		jsonResponse(w, Response{
			Status:  "error",
			Message: string(out) + "\n" + err.Error(),
		})
		return
	}

	jsonResponse(w, Response{
		Status: "ok",
		Data: map[string]string{
			"command": shellCmd,
			"output":  string(out),
		},
	})
}

// VULNERABLE: Unauthenticated endpoint that returns admin token (for B-2 SSRF chain)
func handleAdminToken(w http.ResponseWriter, r *http.Request) {
	username := r.URL.Query().Get("username")
	if username == "" {
		username = "admin"
	}

	jsonResponse(w, Response{
		Status: "ok",
		Data: AdminUser{
			ID:       1,
			Username: username,
			Role:     "admin",
			Token:    adminToken,
		},
	})
}

// VULNERABLE: Unauthenticated endpoint — allows user creation (for B-2)
func handleAdminUsers(w http.ResponseWriter, r *http.Request) {
	if r.Method == "POST" {
		var user map[string]interface{}
		if err := json.NewDecoder(r.Body).Decode(&user); err != nil {
			jsonError(w, "Invalid JSON", 400)
			return
		}
		jsonResponse(w, Response{
			Status:  "ok",
			Message: fmt.Sprintf("用户 %v 创建成功", user["username"]),
		})
		return
	}

	// GET — list users
	jsonResponse(w, Response{
		Status: "ok",
		Data: []AdminUser{
			{ID: 1, Username: "admin", Role: "admin"},
			{ID: 2, Username: "operator", Role: "operator"},
			{ID: 3, Username: "monitor", Role: "viewer"},
		},
	})
}

func jsonResponse(w http.ResponseWriter, resp Response) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	json.NewEncoder(w).Encode(resp)
}

func jsonError(w http.ResponseWriter, msg string, code int) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(code)
	json.NewEncoder(w).Encode(Response{Status: "error", Message: msg})
}
