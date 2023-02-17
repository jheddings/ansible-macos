"""Custom ansible module for managing power settings on macOS."""


class PowerSettings:
    def __init__(self, module):
        self.module = module
        self.props = None

        self._load_current_settings()

    def get(self, source, name):
        sett = self.props.get(source, None)

        if sett is None:
            return None

        return sett.get(name, None)

    def set(self, source, name, value):
        cmd = ["pmset"]

        if source == "battery":
            cmd += ["-b"]
        elif source == "wired":
            cmd += ["-c"]

        cmd += [name, value]

        rc, out, err = self.module.run_command(cmd)

        if rc != 0:
            raise OSError(f"An error occurred while updating power settings: {rc}")

        self._load_current_settings()

    def _load_current_settings(self):
        rc, out, err = self.module.run_command(["pmset", "-g", "custom"])

        if rc != 0:
            raise OSError(f"An error occurred while reading current settings: {rc}")

        self.props = {}
        current_section = None

        for line in out.splitlines(False):
            if line.startswith("Battery Power:"):
                current_section = "battery"
                self.props[current_section] = {}

            elif line.startswith("AC Power:"):
                current_section = "wired"
                self.props[current_section] = {}

            elif current_section is None:
                continue

            (name, value) = line.rsplit(maxsplit=1)
            name = name.strip()
            value = value.strip()
            self.props[current_section][name] = value


def run(module):
    """Run the configured module."""

    pmset = PowerSettings(module)

    source = module.params["source"]
    name = module.params["name"]
    desired_val = module.params["value"]

    orig_val = pmset.get(source, name)

    status = {"changed": False, "original_value": orig_val, "msg": ""}

    if orig_val is None:
        status["msg"] = f"{source}.{name} is not present"

    elif orig_val == desired_val:
        status["msg"] = f"{source}.{name} is current; nothing to do"

    else:
        pmset.set(source, name, desired_val)

        new_val = pmset.get(source, name)
        if new_val != desired_val:
            raise ValueError(f"Could not update {source}.{name}")

        status["msg"] = f"{source}.{name} changed to {desired_val}"

        status["changed"] = True

    return status


def main():
    """Main module entry point."""
    from ansible.module_utils.basic import AnsibleModule

    arg_spec = {
        "name": {"type": "str", "required": True},
        "value": {"type": "str", "required": True},
        "source": {
            "type": "str",
            "choices": [
                "battery",
                "wired",
            ],
        },
    }

    module = AnsibleModule(
        argument_spec=arg_spec,
        supports_check_mode=True,
    )

    result = run(module)
    module.exit_json(**result)


if __name__ == "__main__":
    main()
