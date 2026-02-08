package middleware

import (
	"context"
	"fmt"
	"strings"

	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
	"go.uber.org/zap"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/metadata"
	"google.golang.org/grpc/status"
)

// GRPCAuthInterceptor provides gRPC-level authentication and authorization.
type GRPCAuthInterceptor struct {
	jwtSecret []byte
	logger    *zap.Logger
}

// NewGRPCAuthInterceptor creates a new gRPC auth interceptor.
func NewGRPCAuthInterceptor(jwtSecret string, logger *zap.Logger) *GRPCAuthInterceptor {
	return &GRPCAuthInterceptor{
		jwtSecret: []byte(jwtSecret),
		logger:    logger,
	}
}

// contextKey for storing auth info in context
type grpcContextKey string

const (
	grpcUserIDKey    grpcContextKey = "grpc_user_id"
	grpcUserEmailKey grpcContextKey = "grpc_user_email"
	grpcUserRoleKey  grpcContextKey = "grpc_user_role"
)

// GRPCJWTClaims represents the JWT claims for gRPC auth.
type GRPCJWTClaims struct {
	UserID uuid.UUID `json:"user_id"`
	Email  string    `json:"email"`
	Role   string    `json:"role"`
	jwt.RegisteredClaims
}

// publicMethods are methods that don't require authentication
var publicMethods = map[string]bool{
	"/grpc.health.v1.Health/Check": true,
	"/axiom.auth.v1.Auth/Login":    true,
	"/axiom.auth.v1.Auth/Register": true,
}

// methodPermissions maps gRPC methods to required permissions
var methodPermissions = map[string]string{
	"/axiom.project.v1.Project/Create": PermEditProject,
	"/axiom.project.v1.Project/Delete": PermDeleteProject,
	"/axiom.team.v1.Team/AddMember":    PermManageTeam,
	"/axiom.team.v1.Team/RemoveMember": PermManageTeam,
	"/axiom.budget.v1.Budget/Approve":  PermApproveBudget,
}

// UnaryServerInterceptor returns a gRPC unary interceptor for auth.
func (i *GRPCAuthInterceptor) UnaryServerInterceptor() grpc.UnaryServerInterceptor {
	return func(
		ctx context.Context,
		req interface{},
		info *grpc.UnaryServerInfo,
		handler grpc.UnaryHandler,
	) (interface{}, error) {
		// Check if method is public
		if publicMethods[info.FullMethod] {
			return handler(ctx, req)
		}

		// Authenticate
		newCtx, err := i.authenticate(ctx)
		if err != nil {
			return nil, err
		}

		// Authorize
		if err := i.authorize(newCtx, info.FullMethod); err != nil {
			return nil, err
		}

		return handler(newCtx, req)
	}
}

// StreamServerInterceptor returns a gRPC stream interceptor for auth.
func (i *GRPCAuthInterceptor) StreamServerInterceptor() grpc.StreamServerInterceptor {
	return func(
		srv interface{},
		ss grpc.ServerStream,
		info *grpc.StreamServerInfo,
		handler grpc.StreamHandler,
	) error {
		// Check if method is public
		if publicMethods[info.FullMethod] {
			return handler(srv, ss)
		}

		// Authenticate
		ctx := ss.Context()
		newCtx, err := i.authenticate(ctx)
		if err != nil {
			return err
		}

		// Authorize
		if err := i.authorize(newCtx, info.FullMethod); err != nil {
			return err
		}

		// Wrap the stream with the new context
		wrapped := &wrappedServerStream{
			ServerStream: ss,
			ctx:          newCtx,
		}

		return handler(srv, wrapped)
	}
}

// authenticate extracts and validates the JWT from metadata.
func (i *GRPCAuthInterceptor) authenticate(ctx context.Context) (context.Context, error) {
	md, ok := metadata.FromIncomingContext(ctx)
	if !ok {
		return nil, status.Errorf(codes.Unauthenticated, "missing metadata")
	}

	// Get authorization header
	authHeaders := md.Get("authorization")
	if len(authHeaders) == 0 {
		return nil, status.Errorf(codes.Unauthenticated, "missing authorization header")
	}

	tokenString := strings.TrimPrefix(authHeaders[0], "Bearer ")
	if tokenString == authHeaders[0] {
		return nil, status.Errorf(codes.Unauthenticated, "invalid authorization format")
	}

	// Parse and validate JWT
	token, err := jwt.ParseWithClaims(tokenString, &GRPCJWTClaims{}, func(token *jwt.Token) (interface{}, error) {
		if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
			return nil, fmt.Errorf("unexpected signing method: %v", token.Header["alg"])
		}
		return i.jwtSecret, nil
	})

	if err != nil {
		i.logger.Warn("JWT parse failed", zap.Error(err))
		return nil, status.Errorf(codes.Unauthenticated, "invalid token")
	}

	claims, ok := token.Claims.(*GRPCJWTClaims)
	if !ok || !token.Valid {
		return nil, status.Errorf(codes.Unauthenticated, "invalid token claims")
	}

	// Add claims to context
	ctx = context.WithValue(ctx, grpcUserIDKey, claims.UserID)
	ctx = context.WithValue(ctx, grpcUserEmailKey, claims.Email)
	ctx = context.WithValue(ctx, grpcUserRoleKey, claims.Role)

	return ctx, nil
}

// authorize checks if the user has permission to call the method.
func (i *GRPCAuthInterceptor) authorize(ctx context.Context, method string) error {
	requiredPermission, needsCheck := methodPermissions[method]
	if !needsCheck {
		// No specific permission required, just authentication
		return nil
	}

	role, ok := ctx.Value(grpcUserRoleKey).(string)
	if !ok {
		return status.Errorf(codes.PermissionDenied, "role not found")
	}

	if !hasPermission(role, requiredPermission) {
		i.logger.Warn("permission denied",
			zap.String("method", method),
			zap.String("role", role),
			zap.String("required", requiredPermission),
		)
		return status.Errorf(codes.PermissionDenied, "insufficient permissions")
	}

	return nil
}

// wrappedServerStream wraps grpc.ServerStream with a custom context.
type wrappedServerStream struct {
	grpc.ServerStream
	ctx context.Context
}

func (w *wrappedServerStream) Context() context.Context {
	return w.ctx
}

// GetGRPCUserID extracts the user ID from gRPC context.
func GetGRPCUserID(ctx context.Context) (uuid.UUID, bool) {
	userID, ok := ctx.Value(grpcUserIDKey).(uuid.UUID)
	return userID, ok
}

// GetGRPCUserEmail extracts the user email from gRPC context.
func GetGRPCUserEmail(ctx context.Context) (string, bool) {
	email, ok := ctx.Value(grpcUserEmailKey).(string)
	return email, ok
}

// GetGRPCUserRole extracts the user role from gRPC context.
func GetGRPCUserRole(ctx context.Context) (string, bool) {
	role, ok := ctx.Value(grpcUserRoleKey).(string)
	return role, ok
}
