"""Custom module for managing settings files."""

import os.path
import plistlib
import re


class PlistBuddy:
    """Wrapper for plist data with helpers for dealing with nested keys."""

    def __init__(self, file):
        """Initialize this PlistBuddy from the given filename."""

        self.file = file
        self.changed = False

        if os.path.exists(file):
            with open(file, "rb") as fp:
                self.data = plistlib.load(fp)
        else:
            self.data = {}

    def __delitem__(self, key):
        """Remove the value of a nested key."""
        self.delete(key)

    def __getitem__(self, key):
        """Return the current value of a nested key."""
        return self.get(key)

    def __setitem__(self, key, value):
        """Set the nested key to the given value."""
        self.set(key, value)

    def get(self, key):
        """Return the current value of a nested key."""

        # find the key's path components (ignore leading :'s)
        fields = re.split(r"(?<!\\):", key.lstrip(":"))

        elem = self.data
        for field in fields:
            if field not in elem:
                return None
            elem = elem[field]

        return elem

    def set(self, key, value):
        """Set the nested key to the given value."""

        # find the key's path components (ignore leading :'s)
        fields = re.split(r"(?<!\\):", key.lstrip(":"))

        elem = self.data
        for field in fields[:-1]:
            elem = elem.setdefault(field, {})

        last = fields[-1]
        if elem.get(last, None) != value:
            elem[last] = value
            self.changed = True

    def delete(self, key):
        """Remove the value of a nested key."""

        # find the key's path components (ignore leading :'s)
        fields = re.split(r"(?<!\\):", key.lstrip(":"))

        elem = self.data
        for field in fields[:-1]:
            if field not in elem:
                return
            elem = elem[field]

        last = fields[-1]
        if last in elem:
            del elem[last]
            self.changed = True

    def merge(self, key, value):
        """Merge the contents from value into key.  Returns the number of changes that were
        made to the internal contents.

        For simple types, this simply replaces the key.  For complex type (such as
        dict and array), this will add the contents from `value` to the data.
        """

        entry = self[key]

        # TODO make sure the instance types are compatible

        if entry is None:
            self[key] = value

        elif isinstance(value, list):
            for item in value:
                if item not in entry:
                    entry.append(item)
                    self.changed = True

        elif isinstance(value, dict):
            for name, item in value.items():
                if entry.get(name, None) != item:
                    entry[name] = item
                    self.changed = True

        else:
            self[key] = value

    def save(self):
        """Save back out the current state of the plist data."""

        with open(self.file, "wb") as fp:
            plistlib.dump(self.data, fp)


def run(module):
    """Run the configured module."""

    file = module.params["file"]
    buddy = PlistBuddy(file)

    key = module.params["key"]
    orig_val = buddy[key]

    status = {"changed": False, "original_value": str(orig_val), "msg": ""}

    target_state = module.params["state"]

    if target_state == "absent":
        if orig_val is None:
            status["msg"] = "key not present"
        else:
            del buddy[key]

            status["msg"] = "removed key"

    elif target_state == "replace":
        value = module.params["value"]

        if orig_val == value:
            status["msg"] = "entry exists; nothing to do"

        else:
            buddy[key] = value

            status["msg"] = "replaced item contents"

    elif target_state == "present":
        target_val = module.params["value"]

        if target_val == orig_val:
            status["msg"] = "entry exists; nothing to do"

        else:
            buddy.merge(key, target_val)

            if buddy.changed:
                status["msg"] = "updated item value"
            else:
                status["msg"] = "entry exists; no changes made"

    if buddy.changed:
        status["changed"] = True
        if not module.check_mode:
            buddy.save()

    return status


def main():
    """Main module entry point."""
    from ansible.module_utils.basic import AnsibleModule

    arg_spec = {
        "file": {"type": "str", "required": True},
        "key": {"type": "str", "required": True},
        "state": {
            "type": "str",
            "default": "present",
            "choices": [
                "absent",
                "present",
                "read",
                "replace",
            ],
        },
        "value": {"type": "raw"},
    }

    module = AnsibleModule(
        argument_spec=arg_spec,
        supports_check_mode=True,
    )

    try:
        result = run(module)
        module.exit_json(**result)
    except OSError as oserr:
        err = f"{oserr.strerror} [{oserr.errno}]"
        if oserr.filename:
            err += " -- " + oserr.filename
        module.fail_json(msg=err)


if __name__ == "__main__":
    main()
