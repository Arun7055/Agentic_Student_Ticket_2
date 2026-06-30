import os
import jwt
import httpx
from uuid import uuid4
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_session
from app.models import User

# This tells FastAPI to look for the "Authorization: Bearer <token>" header
security = HTTPBearer()

CLERK_PEM_PUBLIC_KEY = os.getenv("CLERK_PEM_PUBLIC_KEY")
if CLERK_PEM_PUBLIC_KEY:
    # Fix the literal \n characters if loaded weirdly from .env
    CLERK_PEM_PUBLIC_KEY = CLERK_PEM_PUBLIC_KEY.replace("\\n", "\n")

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_session)
) -> User:
    """The Bouncer: Verifies JWT signature and provisions new users on the fly."""
    token = credentials.credentials

    try:
        # 1. Cryptographically verify the token (No network request needed!)
        payload = jwt.decode(
            token,
            CLERK_PEM_PUBLIC_KEY,
            algorithms=["RS256"],
            options={"verify_aud": False} # We don't care about the audience in Dev
        )
        clerk_id = payload.get("sub")
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token signature.")

    # 2. Check if this student already exists in our Postgres DB
    stmt = select(User).where(User.clerk_id == clerk_id)
    user = (await db.execute(stmt)).scalars().first()

    # 3. JUST-IN-TIME PROVISIONING & ACCOUNT LINKING
    if not user:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"https://api.clerk.com/v1/users/{clerk_id}",
                headers={"Authorization": f"Bearer {os.getenv('CLERK_SECRET_KEY')}"}
            )
            
            if res.status_code != 200:
                raise HTTPException(status_code=401, detail="Could not sync user profile from Clerk.")
                
            clerk_data = res.json()
            email = clerk_data["email_addresses"][0]["email_address"]
            
            # ---> NEW LOGIC: Check if this email already exists (e.g., a seeded Faculty member)
            email_stmt = select(User).where(User.email == email)
            existing_user = (await db.execute(email_stmt)).scalars().first()
            
            if existing_user:
                # Link the new Clerk ID to the existing database row
                existing_user.clerk_id = clerk_id
                await db.commit()
                await db.refresh(existing_user)
                user = existing_user
                print(f"🔗 Linked Clerk account to existing profile: {user.full_name} ({user.role})")
            else:
                # Actually a brand new student, create from scratch
                first = clerk_data.get("first_name") or "Student"
                last = clerk_data.get("last_name") or ""
                
                user = User(
                    id=uuid4(),
                    clerk_id=clerk_id,
                    email=email,
                    full_name=f"{first} {last}".strip(),
                    role="STUDENT"
                )
                db.add(user)
                await db.commit()
                await db.refresh(user)
                print(f"🎉 New Freshman Synced: {user.full_name}")

    return user