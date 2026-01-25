package handlers

import (
	"net/http"
	"time"

	"github.com/axiom/api/internal/database"
	"github.com/axiom/api/internal/middleware"
	"github.com/axiom/api/internal/models"
	"github.com/gin-gonic/gin"
	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
	"go.uber.org/zap"
	"golang.org/x/crypto/bcrypt"
)

// AuthHandler handles authentication endpoints
type AuthHandler struct {
	db        *database.Postgres
	jwtSecret string
	logger    *zap.Logger
}

// NewAuthHandler creates a new auth handler
func NewAuthHandler(db *database.Postgres, jwtSecret string, logger *zap.Logger) *AuthHandler {
	return &AuthHandler{db: db, jwtSecret: jwtSecret, logger: logger}
}

// RegisterRequest is the request body for registration
type RegisterRequest struct {
	Email    string `json:"email" binding:"required,email"`
	Name     string `json:"name" binding:"required,min=2"`
	Password string `json:"password" binding:"required,min=8"`
}

// LoginRequest is the request body for login
type LoginRequest struct {
	Email    string `json:"email" binding:"required,email"`
	Password string `json:"password" binding:"required"`
}

// AuthResponse is the response for auth endpoints
type AuthResponse struct {
	Token        string       `json:"token"`
	RefreshToken string       `json:"refresh_token"`
	ExpiresAt    time.Time    `json:"expires_at"`
	User         *models.User `json:"user"`
}

// Register creates a new user account
func (h *AuthHandler) Register(c *gin.Context) {
	var req RegisterRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// Hash password
	hashedPassword, err := bcrypt.GenerateFromPassword([]byte(req.Password), bcrypt.DefaultCost)
	if err != nil {
		h.logger.Error("failed to hash password", zap.Error(err))
		c.JSON(http.StatusInternalServerError, gin.H{"error": "internal server error"})
		return
	}

	// Insert user
	userID := uuid.New()
	query := `
		INSERT INTO users (id, email, name, password_hash, role, trust_dial_default)
		VALUES ($1, $2, $3, $4, 'developer', 5)
		RETURNING created_at, updated_at
	`

	var user models.User
	user.ID = userID
	user.Email = req.Email
	user.Name = req.Name
	user.Role = "developer"
	user.TrustDialDefault = 5

	err = h.db.Pool().QueryRow(c.Request.Context(), query, userID, req.Email, req.Name, string(hashedPassword)).
		Scan(&user.CreatedAt, &user.UpdatedAt)

	if err != nil {
		h.logger.Error("failed to create user", zap.Error(err))
		c.JSON(http.StatusConflict, gin.H{"error": "email already exists"})
		return
	}

	// Generate tokens
	token, refreshToken, expiresAt, err := h.generateTokens(&user)
	if err != nil {
		h.logger.Error("failed to generate tokens", zap.Error(err))
		c.JSON(http.StatusInternalServerError, gin.H{"error": "internal server error"})
		return
	}

	c.JSON(http.StatusCreated, AuthResponse{
		Token:        token,
		RefreshToken: refreshToken,
		ExpiresAt:    expiresAt,
		User:         &user,
	})
}

// Login authenticates a user
func (h *AuthHandler) Login(c *gin.Context) {
	var req LoginRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// Find user
	query := `
		SELECT id, email, name, password_hash, role, trust_dial_default, created_at, updated_at
		FROM users WHERE email = $1
	`

	var user models.User
	var passwordHash string
	err := h.db.Pool().QueryRow(c.Request.Context(), query, req.Email).
		Scan(&user.ID, &user.Email, &user.Name, &passwordHash, &user.Role, &user.TrustDialDefault, &user.CreatedAt, &user.UpdatedAt)

	if err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "invalid credentials"})
		return
	}

	// Verify password
	if err := bcrypt.CompareHashAndPassword([]byte(passwordHash), []byte(req.Password)); err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "invalid credentials"})
		return
	}

	// Generate tokens
	token, refreshToken, expiresAt, err := h.generateTokens(&user)
	if err != nil {
		h.logger.Error("failed to generate tokens", zap.Error(err))
		c.JSON(http.StatusInternalServerError, gin.H{"error": "internal server error"})
		return
	}

	c.JSON(http.StatusOK, AuthResponse{
		Token:        token,
		RefreshToken: refreshToken,
		ExpiresAt:    expiresAt,
		User:         &user,
	})
}

// RefreshToken refreshes an access token
func (h *AuthHandler) RefreshToken(c *gin.Context) {
	// Implementation for refresh token
	c.JSON(http.StatusNotImplemented, gin.H{"error": "not implemented"})
}

// GetCurrentUser returns the current authenticated user
func (h *AuthHandler) GetCurrentUser(c *gin.Context) {
	userID, ok := middleware.GetUserID(c)
	if !ok {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "unauthorized"})
		return
	}

	query := `
		SELECT id, email, name, role, trust_dial_default, created_at, updated_at
		FROM users WHERE id = $1
	`

	var user models.User
	err := h.db.Pool().QueryRow(c.Request.Context(), query, userID).
		Scan(&user.ID, &user.Email, &user.Name, &user.Role, &user.TrustDialDefault, &user.CreatedAt, &user.UpdatedAt)

	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "user not found"})
		return
	}

	c.JSON(http.StatusOK, user)
}

// UpdateSettings updates user settings
func (h *AuthHandler) UpdateSettings(c *gin.Context) {
	c.JSON(http.StatusNotImplemented, gin.H{"error": "not implemented"})
}

func (h *AuthHandler) generateTokens(user *models.User) (string, string, time.Time, error) {
	expiresAt := time.Now().Add(24 * time.Hour)

	claims := middleware.Claims{
		UserID: user.ID,
		Email:  user.Email,
		Role:   user.Role,
		RegisteredClaims: jwt.RegisteredClaims{
			ExpiresAt: jwt.NewNumericDate(expiresAt),
			IssuedAt:  jwt.NewNumericDate(time.Now()),
			Subject:   user.ID.String(),
		},
	}

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	tokenString, err := token.SignedString([]byte(h.jwtSecret))
	if err != nil {
		return "", "", time.Time{}, err
	}

	// Simple refresh token (in production, store in database)
	refreshToken := uuid.New().String()

	return tokenString, refreshToken, expiresAt, nil
}
