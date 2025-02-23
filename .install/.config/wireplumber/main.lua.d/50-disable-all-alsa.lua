
-- Disable all alsa cards under wireplumber (the PipeWire session manager)

alsa_monitor.rules = {
  {
    matches = {
      {
        { "device.name", "matches", "alsa_card.*" }
      },
    },

    apply_properties = {
      ["device.disabled"] = true,
    },
  },
}

