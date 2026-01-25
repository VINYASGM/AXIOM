-- Seeding data for verification
-- 1. Ensure Organization exists
INSERT INTO organizations (id, name, security_context)
VALUES ('11111111-1111-1111-1111-111111111111', 'Axiom Dev Org', 'private')
ON CONFLICT (id) DO NOTHING;

-- 2. Ensure Project exists (linked to default Dev User)
INSERT INTO projects (id, name, org_id, owner_id)
VALUES (
    '22222222-2222-2222-2222-222222222222', 
    'Axiom Core Loop Test', 
    '11111111-1111-1111-1111-111111111111', 
    (SELECT id FROM users WHERE email='dev@axiom.local')
)
ON CONFLICT (id) DO NOTHING;
