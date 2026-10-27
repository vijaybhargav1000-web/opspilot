# Permission Error Runbook

## Purpose
Investigate access failures involving files, databases, APIs, cloud resources, or service identities.

## Symptoms
- Permission denied
- Access denied
- Unauthorized
- Forbidden
- AccessDenied

## Investigation
1. Identify the resource, operation, timestamp, and request ID.
2. Determine which user, service account, or role made the request.
3. Inspect the applicable identity permissions and resource-level policies.
4. Check recent role, policy, credential, and resource-ownership changes.
5. Review audit logs for the denied operation.

## Remediation
1. Correct an incorrect resource name or identity configuration if confirmed.
2. Request the minimum permission needed for the documented operation.
3. Follow the organization's approval process for access changes.
4. Rotate exposed credentials through the approved secret-management process.
5. Retest using the intended service identity.

## Validation
Verify that the required operation succeeds and unrelated access remains restricted.

## Safety
Never bypass access controls, grant broad administrator permissions as a shortcut, or print secrets into logs.
