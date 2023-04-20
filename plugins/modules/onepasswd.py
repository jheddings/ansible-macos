"""Custom ansible module for working with 1Password via CLI."""

import json

from ansible.module_utils.basic import AnsibleModule


class OnePasswordCLI:
    def __init__(self, module: AnsibleModule, account=None, vault=None, dry_run=False):
        self.module = module
        self.dry_run = dry_run

        self.vault = vault
        self.account = account

    def cli(self, *args):
        cmd = ["op", "item"]

        if self.account is not None:
            cmd += ("--account", self.account)

        if self.vault is not None:
            cmd += ("--vault", self.vault)

        cmd.extend(args)

        return cmd

    def set(self, name, field, value):
        cmd = self.cli("edit", name, f"{field}={value}")

        if not self.dry_run:
            self.module.run_command(cmd, check_rc=True)

    def parse_field_data(self, data):
        parsed = {
            "label": data["label"],
            "reference": data.get("reference", None),
            "value": data.get("value", None),
        }

        return parsed

    def info(self, name):
        cmd = self.cli("get", name, "--format=json")
        rc, out, err = self.module.run_command(cmd)

        if rc == 0:
            info = json.loads(out)

            return {
                "changed": False,
                "msg": name,
                "item": info["title"],
                "vault": info["vault"]["name"],
                "data": {
                    field["id"]: field.get("value", None) for field in info["fields"]
                },
            }

        if rc == 1:
            return {
                "changed": False,
                "failed": True,
                "msg": f"Entry not found -- {name}",
            }

        raise OSError(f"An error occurred while reading current settings: {rc}")

    def create(self, name, fields: dict, replace=True):
        # get the current entry (if it exists)
        info = self.info(name)
        current_values = info.get("data", None)

        changed = False

        # for each target field, determine appropriate action
        for field, target_value in fields.items():
            needs_update = False

            if current_values is None:
                current_values = {}
                needs_update = True

            elif field not in current_values:
                needs_update = True

            elif replace:
                if current_values[field] != target_value:
                    needs_update = True

            if needs_update:
                self.set(name, field, target_value)
                current_values[field] = target_value
                changed = True

        return {
            "changed": changed,
            "msg": name,
            "item": info["item"],
            "vault": info["vault"],
            "data": current_values,
        }


def run(module):
    """Run the configured module."""

    target_state = module.params["state"]
    vault = module.params["vault"]
    account = module.params["account"]
    name = module.params["name"]
    fields = module.params["fields"]

    op = OnePasswordCLI(module, account=account, vault=vault)

    status = {"changed": False, "msg": ""}

    if target_state == "info":
        return op.info(name)

    if target_state == "present":
        return op.create(name, fields, replace=False)

    if target_state == "update":
        return op.create(name, fields, replace=True)

    return status


def main():
    """Main module entry point."""

    arg_spec = {
        "name": {"type": "str", "required": True},
        "vault": {"type": "str", "default": None},
        "account": {"type": "str", "default": None},
        "fields": {"type": "dict", "default": None},
        "state": {
            "type": "str",
            "default": "present",
            "choices": [
                "info",
                "present",
                "update",
            ],
        },
    }

    module = AnsibleModule(
        argument_spec=arg_spec,
        supports_check_mode=True,
        required_if=[
            ("state", "update", ["fields"]),
            ("state", "present", ["fields"]),
        ],
    )

    result = run(module)
    module.exit_json(**result)


if __name__ == "__main__":
    main()
