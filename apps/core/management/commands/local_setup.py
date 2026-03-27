from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from django.core.management import BaseCommand, CommandError, call_command


class Command(BaseCommand):
    help = "Rebuild local assets, sync the database, seed demo content, and bootstrap an admin user."

    def add_arguments(self, parser):
        parser.add_argument("--skip-assets", action="store_true")
        parser.add_argument("--skip-seed", action="store_true")
        parser.add_argument("--skip-admin", action="store_true")
        parser.add_argument("--install-frontend", action="store_true")
        parser.add_argument("--admin-email", default=None)
        parser.add_argument("--admin-password", default=None)

    def handle(self, *args, **options):
        base_dir = Path(__file__).resolve().parents[4]

        if not options["skip_assets"]:
            self.build_assets(base_dir=base_dir, install_frontend=options["install_frontend"])

        self.stdout.write(self.style.NOTICE("Running prerequisite Django migrations..."))
        for app_label in ("contenttypes", "auth", "catalog"):
            call_command("migrate", app_label, interactive=False)

        self.stdout.write(
            self.style.NOTICE("Synchronizing app tables without migrations (run-syncdb)...")
        )
        call_command("migrate", run_syncdb=True, interactive=False)

        self.stdout.write(self.style.NOTICE("Running dependent Django migrations..."))
        for app_label in ("admin", "sessions", "sites"):
            call_command("migrate", app_label, interactive=False)

        self.stdout.write(self.style.NOTICE("Applying remaining app migrations..."))
        call_command("migrate", interactive=False)

        if not options["skip_seed"]:
            self.stdout.write(self.style.NOTICE("Seeding demo storefront content..."))
            call_command("seed_demo_store")

        if not options["skip_admin"]:
            self.stdout.write(self.style.NOTICE("Bootstrapping admin user..."))
            bootstrap_kwargs = {}
            if options["admin_email"]:
                bootstrap_kwargs["email"] = options["admin_email"]
            if options["admin_password"]:
                bootstrap_kwargs["password"] = options["admin_password"]
            call_command("bootstrap_admin", **bootstrap_kwargs)

        self.stdout.write(self.style.SUCCESS("Local Nest & Whisk setup complete."))
        self.stdout.write("Start the site with: python manage.py runserver 127.0.0.1:8001")

    def build_assets(self, *, base_dir: Path, install_frontend: bool) -> None:
        node_cmd = shutil.which("node")
        npm_cmd = shutil.which("npm.cmd") or shutil.which("npm")
        node_cmd_str = str(node_cmd) if node_cmd else None
        npm_cmd_str = str(npm_cmd) if npm_cmd else None
        vite_bin = base_dir / "node_modules" / "vite" / "bin" / "vite.js"
        package_lock = base_dir / "package-lock.json"
        npm_install_args = [npm_cmd_str, "ci"] if package_lock.exists() else [npm_cmd_str, "install"]

        if not node_cmd_str:
            raise CommandError("Node.js is required to build frontend assets locally.")

        if install_frontend or not vite_bin.exists():
            if not npm_cmd_str:
                raise CommandError("npm is required to install frontend dependencies locally.")
            self.stdout.write(self.style.NOTICE("Installing frontend dependencies..."))
            subprocess.run(npm_install_args, cwd=str(base_dir), check=True)

        if not vite_bin.exists():
            raise CommandError("Vite is not installed. Re-run with --install-frontend.")

        self.stdout.write(self.style.NOTICE("Building frontend assets..."))
        subprocess.run([node_cmd_str, str(vite_bin), "build"], cwd=str(base_dir), check=True)

