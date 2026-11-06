import argparse
import asyncio
import getpass

from sqlalchemy import select

from app.db.models import load_models
from app.db.session import SessionFactory, engine
from app.modules.auth.models import User
from app.modules.auth.schemas import UserCreate
from app.modules.auth.service import create_user


async def provision(args):
    load_models()
    data = UserCreate(
        email=args.email,
        full_name=args.name,
        role=args.role,
        password=getpass.getpass("Password (minimum 12 characters): "),
    )
    async with SessionFactory.begin() as db:
        if await db.scalar(select(User.id).where(User.email == str(data.email).lower())):
            raise SystemExit("Email already exists; no changes made")
        user = await create_user(db, data, data.role)
        print(f"Created {user.role}: {user.id}")
    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Provision a local account; never logs passwords")
    parser.add_argument("email")
    parser.add_argument("--name", required=True)
    parser.add_argument(
        "--role", choices=["admin", "client", "employee", "audience"], default="admin"
    )
    asyncio.run(provision(parser.parse_args()))
