package middleware

import (
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
)

const testJWTSecret = "test-secret-key-for-unit-tests"

func generateTestToken(t *testing.T, userID uuid.UUID, email, role string, expired bool) string {
	t.Helper()
	expiry := time.Now().Add(1 * time.Hour)
	if expired {
		expiry = time.Now().Add(-1 * time.Hour)
	}
	claims := &Claims{
		UserID: userID,
		Email:  email,
		Role:   role,
		RegisteredClaims: jwt.RegisteredClaims{
			ExpiresAt: jwt.NewNumericDate(expiry),
			IssuedAt:  jwt.NewNumericDate(time.Now()),
		},
	}
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	tokenString, err := token.SignedString([]byte(testJWTSecret))
	if err != nil {
		t.Fatalf("failed to sign token: %v", err)
	}
	return tokenString
}

func setupRouter() *gin.Engine {
	gin.SetMode(gin.TestMode)
	r := gin.New()
	return r
}

func TestAuth_NoHeader(t *testing.T) {
	r := setupRouter()
	r.GET("/test", Auth(testJWTSecret), func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "ok"})
	})
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/test", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusUnauthorized {
		t.Errorf("expected 401, got %d", w.Code)
	}
}

func TestAuth_InvalidFormat(t *testing.T) {
	r := setupRouter()
	r.GET("/test", Auth(testJWTSecret), func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "ok"})
	})
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/test", nil)
	req.Header.Set("Authorization", "NotBearer sometoken")
	r.ServeHTTP(w, req)

	if w.Code != http.StatusUnauthorized {
		t.Errorf("expected 401, got %d", w.Code)
	}
}

func TestAuth_ExpiredToken(t *testing.T) {
	userID := uuid.New()
	token := generateTestToken(t, userID, "test@axiom.dev", "user", true)

	r := setupRouter()
	r.GET("/test", Auth(testJWTSecret), func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "ok"})
	})
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/test", nil)
	req.Header.Set("Authorization", "Bearer "+token)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusUnauthorized {
		t.Errorf("expected 401 for expired token, got %d", w.Code)
	}
}

func TestAuth_ValidToken(t *testing.T) {
	userID := uuid.New()
	token := generateTestToken(t, userID, "test@axiom.dev", "admin", false)

	r := setupRouter()
	r.GET("/test", Auth(testJWTSecret), func(c *gin.Context) {
		uid, exists := GetUserID(c)
		if !exists {
			t.Error("expected user_id in context")
		}
		if uid != userID {
			t.Errorf("expected user_id %s, got %s", userID, uid)
		}
		c.JSON(http.StatusOK, gin.H{"user_id": uid.String()})
	})
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/test", nil)
	req.Header.Set("Authorization", "Bearer "+token)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected 200 for valid token, got %d", w.Code)
	}
}

func TestAuth_WrongSecret(t *testing.T) {
	userID := uuid.New()
	// Sign with a different secret
	claims := &Claims{
		UserID: userID,
		Email:  "test@axiom.dev",
		Role:   "user",
		RegisteredClaims: jwt.RegisteredClaims{
			ExpiresAt: jwt.NewNumericDate(time.Now().Add(1 * time.Hour)),
		},
	}
	jwtToken := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	tokenString, _ := jwtToken.SignedString([]byte("wrong-secret"))

	r := setupRouter()
	r.GET("/test", Auth(testJWTSecret), func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "ok"})
	})
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/test", nil)
	req.Header.Set("Authorization", "Bearer "+tokenString)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusUnauthorized {
		t.Errorf("expected 401 for wrong secret, got %d", w.Code)
	}
}

func TestGetUserID_NotSet(t *testing.T) {
	gin.SetMode(gin.TestMode)
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	_, exists := GetUserID(c)
	if exists {
		t.Error("expected false for missing user_id in context")
	}
}
