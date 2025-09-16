import ast


class Config:
    def __init__(self, config_path):
        self.config_path = config_path
        self.params = {}
        self.sensors = []
        self.load()

    def load(self):
        with open(self.config_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip('"')
                    if key == "sensors":
                        self.sensors = ast.literal_eval(value)
                    else:
                        self.params[key] = value
