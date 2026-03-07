from dataclasses import dataclass


@dataclass
class RuntimeManifest:
    platform: str

    @property
    def backend_priority(self):
        if self.platform == "win32":
            return ["cuda", "hip", "vulkan", "cpu"]
        if self.platform == "darwin":
            return ["metal_coreml", "cpu"]
        return ["cpu"]
