# Versa Geometry Studio — acquisition plan

Profile: ZEISS Versa — 2048 × 2048, 13.5 µm, 0.4×
Objective: 0.4× (unconfigured)

Source a = 205.0 mm; scintillator b = 267.32 mm; total D = 472.32 mm.
Geometrical magnification = 2.3040000000000003×; optical × geometrical = 0.9216000000000002×.
Acquired field = 29.999999999999993 × 29.999999999999993 mm at 14.648437499999996 µm/pixel.
Output = 2048 × 2048 binned pixels; full usable = 2048 × 2048.
Angle convention: full diagonal, active envelope; limit = 12.0 degrees, buffer = 0.02 degrees.

## Equations and conventions

M_g = (a+b)/a; M_total = m M_g; Δ = k p/(m M_g); FOV = N_out Δ.
W = N_usable p/m; α = atan(R/D); full opening θ = 2α.
Ray from S=(-a,0,0) through P=(x,y,z): t=(a+b)/(a+x); detector=(b,t y,t z).
Geometry lengths are mm; p is converted from µm to mm; trigonometry uses radians.
Pixel centers: u=y_camera/(k p)+(N_x,out−1)/2. Physical edges clip rays; displayed vertical axis is downward.
Binning changes acquired sampling and count, not full usable FOV. Sampling is not measured spatial resolution.

## Planning and coverage

Solver: feasible. Minimum separation: a = 202.169568 mm, b = 263.629116 mm, D = 465.798684 mm. Distance family b = 1.304 a. Angle equality D = 465.016663 mm; buffered boundary D = 465.798684 mm (0.02° in full convention). Active: sampling lower magnification, coverage upper magnification, buffered acquisition angle. Geometry does not predict exposure time or SNR.
Exact locks → minimum D → finest sampling with coverage → closest current pair
Current specimen clipping: False; equivalent center-plane projected extent = (28.345679012345677, 28.345679012345677) mm.
Instantaneous coverage is separate from full-rotation coverage. A discrete sweep is a sampled assessment, not a guarantee.
Synthetic transmission: I/I0 = exp(−μ_host ℓ_host − (μ_inclusion−μ_host) ℓ_inclusion), finite analytic ray intersections.
This illustrative, noise-free monochromatic preview does not predict a calibrated ZEISS scan, exposure, SNR, or true resolution.

## Constraints and calibration

Model demonstration. Hardware travel and clearances are unconfigured. Legacy manual values require local confirmation; stage coordinates are not physical distances.
Confirmed hardware violations: none among configured constraints
The legacy 135 mm rule is a stage-coordinate reference for 0.4× only. It is applied only after confirmation AND a verified signed affine coordinate mapping.
Unconfigured travel, optical geometry, clearances, objective availability and source emission aperture are unknown. Sliders are model exploration ranges.

## Parameters and provenance

| Parameter | Value | Units | Role / provenance |
|---|---|---|---|
| a_mm | 205.0 | mm | derived |
| b_mm | 267.32 | mm | derived |
| D_mm | 472.32 | mm | derived |
| geometrical_m | 2.3040000000000003 | dimensionless | derived |
| total_m | 0.9216000000000002 | dimensionless | derived |
| camera_x_mm | 27.648 | mm | derived |
| camera_y_mm | 27.648 | mm | derived |
| scintillator_x_mm | 69.11999999999999 | mm | derived |
| scintillator_y_mm | 69.11999999999999 | mm | derived |
| crop_scintillator_x_mm | 69.11999999999999 | mm | derived |
| crop_scintillator_y_mm | 69.11999999999999 | mm | derived |
| output_nx | 2048 | pixels | derived |
| output_ny | 2048 | pixels | derived |
| crop_nx | 2048 | pixels | derived |
| crop_ny | 2048 | pixels | derived |
| sampling_um | 14.648437499999996 | µm/pixel | derived |
| fov_x_mm | 29.999999999999993 | mm | derived |
| fov_y_mm | 29.999999999999993 | mm | derived |
| crop_fov_x_mm | 29.999999999999993 | mm | derived |
| crop_fov_y_mm | 29.999999999999993 | mm | derived |
| half_angles_rad.horizontal | 0.07304056530311932 | rad | derived |
| full_angles_deg.horizontal | 8.369832250236831 | degrees | derived |
| half_angles_rad.vertical | 0.07304056530311932 | rad | derived |
| full_angles_deg.vertical | 8.369832250236831 | degrees | derived |
| half_angles_rad.diagonal | 0.10311204796392184 | rad | derived |
| full_angles_deg.diagonal | 11.81577033056647 | degrees | derived |
| crop_half_angles_rad.horizontal | 0.07304056530311932 | rad | derived |
| crop_full_angles_deg.horizontal | 8.369832250236831 | degrees | derived |
| crop_half_angles_rad.vertical | 0.07304056530311932 | rad | derived |
| crop_full_angles_deg.vertical | 8.369832250236831 | degrees | derived |
| crop_half_angles_rad.diagonal | 0.10311204796392184 | rad | derived |
| crop_full_angles_deg.diagonal | 11.81577033056647 | degrees | derived |
| detector.nx | 2048 | pixels | input |
| detector.ny | 2048 | pixels | input |
| detector.pitch_um | 13.5 | µm | input |
| detector.optical_m | 0.4 | dimensionless | input |
| detector.binning | 1 | dimensionless | input |
| detector.usable_nx | unconfigured | pixels | input |
| detector.usable_ny | unconfigured | pixels | input |
| detector.image_circle_mm | unconfigured | mm | input |
| detector.crop_nx | unconfigured | pixels | input |
| detector.crop_ny | unconfigured | pixels | input |
| detector.flip_y | False | dimensionless | input |
| detector.flip_z | False | dimensionless | input |
| requirements.sampling_um | 14.6484375 | µm | input |
| requirements.sampling_mode | exact | dimensionless | input |
| requirements.fov_x_mm | 30.0 | mm | input |
| requirements.fov_y_mm | 30.0 | mm | input |
| requirements.margin_mm | 0.0 | mm | input |
| requirements.fixed_kind | none | dimensionless | input |
| requirements.fixed_mm | unconfigured | mm | input |
| requirements.goal | minimum separation | dimensionless | input |
| angle.limit_deg | 12.0 | degrees | input |
| angle.axis | diagonal | dimensionless | input |
| angle.convention | full | dimensionless | input |
| angle.envelope | active | dimensionless | input |
| angle.strict | True | dimensionless | input |
| angle.buffer_deg | 0.02 | degrees | input |
| phantom.shape | cuboid | dimensionless | input |
| phantom.width_mm | 28.0 | mm | input |
| phantom.height_mm | 28.0 | mm | input |
| phantom.depth_mm | 5.0 | mm | input |
| phantom.offset_x_mm | 0.0 | mm | input |
| phantom.offset_y_mm | 0.0 | mm | input |
| phantom.offset_z_mm | 0.0 | mm | input |
| phantom.rotation_deg | 0.0 | degrees | input |
| phantom.mu_mm_inv | 0.055 | mm^-1 | input |
| phantom.inclusion_mu_mm_inv | 0.22 | mm^-1 | input |
| phantom.roi_width_mm | 10.0 | mm | input |
| phantom.roi_height_mm | 10.0 | mm | input |
| phantom.roi_depth_mm | 3.0 | mm | input |
| phantom.roi_enabled | False | dimensionless | input |
| phantom.roi_offset_x_mm | 0.0 | mm | input |
| phantom.roi_offset_y_mm | 0.0 | mm | input |
| phantom.roi_offset_z_mm | 0.0 | mm | input |
| profile.a_min | unconfigured | mm | user supplied; confirmed=False;    |
| profile.a_max | unconfigured | mm | user supplied; confirmed=False;    |
| profile.b_min | unconfigured | mm | user supplied; confirmed=False;    |
| profile.b_max | unconfigured | mm | user supplied; confirmed=False;    |
| profile.D_min | unconfigured | mm | user supplied; confirmed=False;    |
| profile.D_max | unconfigured | mm | user supplied; confirmed=False;    |
| profile.source_clearance | unconfigured | mm | user supplied; confirmed=False;    |
| profile.detector_clearance | unconfigured | mm | user supplied; confirmed=False;    |
| profile.name | ZEISS Versa — 2048 × 2048, 13.5 µm, 0.4× | text | input |
| profile.objective | 0.4× | text | input |
| profile.legacy_stage_min | 135.0 | mm | legacy reference, stage coordinates; confirmed=False |
| profile.mapping_verified | False | dimensionless | calibration |
| mode | Explore geometry | text | input |

Full profile provenance and coordinate mapping:

```json
{
  "name": "ZEISS Versa — 2048 × 2048, 13.5 µm, 0.4×",
  "selected_objective": "0.4×",
  "objectives": {
    "0.4×": {
      "detector": {
        "nx": 2048,
        "ny": 2048,
        "pitch_um": 13.5,
        "optical_m": 0.4,
        "binning": 1,
        "usable_nx": null,
        "usable_ny": null,
        "image_circle_mm": null,
        "crop_nx": null,
        "crop_ny": null,
        "flip_y": false,
        "flip_z": false,
        "provenance": {
          "nx": {
            "value": 2048,
            "units": "pixels",
            "origin": "reference",
            "confirmed": false,
            "source": "https://www.physics.purdue.edu/xrm/new-users/training/Xradia_Versa_Users_Guide_v11x_510.pdf",
            "version": "v11.x, Table H-6",
            "date": ""
          },
          "ny": {
            "value": 2048,
            "units": "pixels",
            "origin": "reference",
            "confirmed": false,
            "source": "https://www.physics.purdue.edu/xrm/new-users/training/Xradia_Versa_Users_Guide_v11x_510.pdf",
            "version": "v11.x, Table H-6",
            "date": ""
          },
          "pitch_um": {
            "value": 13.5,
            "units": "µm",
            "origin": "reference",
            "confirmed": false,
            "source": "https://www.physics.purdue.edu/xrm/new-users/training/Xradia_Versa_Users_Guide_v11x_510.pdf",
            "version": "v11.x, Table H-6",
            "date": ""
          },
          "optical_m": {
            "value": 0.4,
            "units": "×",
            "origin": "nominal",
            "confirmed": false,
            "source": "",
            "version": "",
            "date": ""
          }
        }
      },
      "availability": "unconfigured",
      "bounds": {},
      "notes": "Nominal optical scale; confirm installed configuration."
    },
    "4×": {
      "detector": {
        "nx": 2048,
        "ny": 2048,
        "pitch_um": 13.5,
        "optical_m": 4,
        "binning": 1,
        "usable_nx": null,
        "usable_ny": null,
        "image_circle_mm": null,
        "crop_nx": null,
        "crop_ny": null,
        "flip_y": false,
        "flip_z": false,
        "provenance": {
          "nx": {
            "value": 2048,
            "units": "pixels",
            "origin": "reference",
            "confirmed": false,
            "source": "https://www.physics.purdue.edu/xrm/new-users/training/Xradia_Versa_Users_Guide_v11x_510.pdf",
            "version": "v11.x, Table H-6",
            "date": ""
          },
          "ny": {
            "value": 2048,
            "units": "pixels",
            "origin": "reference",
            "confirmed": false,
            "source": "https://www.physics.purdue.edu/xrm/new-users/training/Xradia_Versa_Users_Guide_v11x_510.pdf",
            "version": "v11.x, Table H-6",
            "date": ""
          },
          "pitch_um": {
            "value": 13.5,
            "units": "µm",
            "origin": "reference",
            "confirmed": false,
            "source": "https://www.physics.purdue.edu/xrm/new-users/training/Xradia_Versa_Users_Guide_v11x_510.pdf",
            "version": "v11.x, Table H-6",
            "date": ""
          },
          "optical_m": {
            "value": 4,
            "units": "×",
            "origin": "nominal",
            "confirmed": false,
            "source": "",
            "version": "",
            "date": ""
          }
        }
      },
      "availability": "unconfigured",
      "bounds": {},
      "notes": "Nominal optical scale; confirm installed configuration."
    },
    "20×": {
      "detector": {
        "nx": 2048,
        "ny": 2048,
        "pitch_um": 13.5,
        "optical_m": 20,
        "binning": 1,
        "usable_nx": null,
        "usable_ny": null,
        "image_circle_mm": null,
        "crop_nx": null,
        "crop_ny": null,
        "flip_y": false,
        "flip_z": false,
        "provenance": {
          "nx": {
            "value": 2048,
            "units": "pixels",
            "origin": "reference",
            "confirmed": false,
            "source": "https://www.physics.purdue.edu/xrm/new-users/training/Xradia_Versa_Users_Guide_v11x_510.pdf",
            "version": "v11.x, Table H-6",
            "date": ""
          },
          "ny": {
            "value": 2048,
            "units": "pixels",
            "origin": "reference",
            "confirmed": false,
            "source": "https://www.physics.purdue.edu/xrm/new-users/training/Xradia_Versa_Users_Guide_v11x_510.pdf",
            "version": "v11.x, Table H-6",
            "date": ""
          },
          "pitch_um": {
            "value": 13.5,
            "units": "µm",
            "origin": "reference",
            "confirmed": false,
            "source": "https://www.physics.purdue.edu/xrm/new-users/training/Xradia_Versa_Users_Guide_v11x_510.pdf",
            "version": "v11.x, Table H-6",
            "date": ""
          },
          "optical_m": {
            "value": 20,
            "units": "×",
            "origin": "nominal",
            "confirmed": false,
            "source": "",
            "version": "",
            "date": ""
          }
        }
      },
      "availability": "unconfigured",
      "bounds": {},
      "notes": "Nominal optical scale; confirm installed configuration."
    },
    "40×": {
      "detector": {
        "nx": 2048,
        "ny": 2048,
        "pitch_um": 13.5,
        "optical_m": 40,
        "binning": 1,
        "usable_nx": null,
        "usable_ny": null,
        "image_circle_mm": null,
        "crop_nx": null,
        "crop_ny": null,
        "flip_y": false,
        "flip_z": false,
        "provenance": {
          "nx": {
            "value": 2048,
            "units": "pixels",
            "origin": "reference",
            "confirmed": false,
            "source": "https://www.physics.purdue.edu/xrm/new-users/training/Xradia_Versa_Users_Guide_v11x_510.pdf",
            "version": "v11.x, Table H-6",
            "date": ""
          },
          "ny": {
            "value": 2048,
            "units": "pixels",
            "origin": "reference",
            "confirmed": false,
            "source": "https://www.physics.purdue.edu/xrm/new-users/training/Xradia_Versa_Users_Guide_v11x_510.pdf",
            "version": "v11.x, Table H-6",
            "date": ""
          },
          "pitch_um": {
            "value": 13.5,
            "units": "µm",
            "origin": "reference",
            "confirmed": false,
            "source": "https://www.physics.purdue.edu/xrm/new-users/training/Xradia_Versa_Users_Guide_v11x_510.pdf",
            "version": "v11.x, Table H-6",
            "date": ""
          },
          "optical_m": {
            "value": 40,
            "units": "×",
            "origin": "nominal",
            "confirmed": false,
            "source": "",
            "version": "",
            "date": ""
          }
        }
      },
      "availability": "unconfigured",
      "bounds": {},
      "notes": "Nominal optical scale; confirm installed configuration."
    }
  },
  "bounds": {
    "a_min": {
      "value": null,
      "units": "mm",
      "origin": "user supplied",
      "confirmed": false,
      "source": "",
      "version": "",
      "date": ""
    },
    "a_max": {
      "value": null,
      "units": "mm",
      "origin": "user supplied",
      "confirmed": false,
      "source": "",
      "version": "",
      "date": ""
    },
    "b_min": {
      "value": null,
      "units": "mm",
      "origin": "user supplied",
      "confirmed": false,
      "source": "",
      "version": "",
      "date": ""
    },
    "b_max": {
      "value": null,
      "units": "mm",
      "origin": "user supplied",
      "confirmed": false,
      "source": "",
      "version": "",
      "date": ""
    },
    "D_min": {
      "value": null,
      "units": "mm",
      "origin": "user supplied",
      "confirmed": false,
      "source": "",
      "version": "",
      "date": ""
    },
    "D_max": {
      "value": null,
      "units": "mm",
      "origin": "user supplied",
      "confirmed": false,
      "source": "",
      "version": "",
      "date": ""
    },
    "source_clearance": {
      "value": null,
      "units": "mm",
      "origin": "user supplied",
      "confirmed": false,
      "source": "",
      "version": "",
      "date": ""
    },
    "detector_clearance": {
      "value": null,
      "units": "mm",
      "origin": "user supplied",
      "confirmed": false,
      "source": "",
      "version": "",
      "date": ""
    }
  },
  "mapping": {
    "verified": false,
    "coeff_a": null,
    "coeff_b": null,
    "offset_mm": null,
    "source": ""
  },
  "legacy_stage_min": {
    "value": 135.0,
    "units": "mm",
    "origin": "reference",
    "confirmed": false,
    "source": "https://www.physics.purdue.edu/xrm/new-users/training/Xradia_Versa_Users_Guide_v11x_510.pdf",
    "version": "v11.x, Table 2-3 (0.4× only)",
    "date": ""
  },
  "focal_spot_um": {
    "value": null,
    "units": "µm",
    "origin": "user supplied",
    "confirmed": false,
    "source": "",
    "version": "",
    "date": ""
  },
  "notes": "Model demonstration. Hardware travel and clearances are unconfigured. Legacy manual values require local confirmation; stage coordinates are not physical distances."
}
```

[ZEISS legacy guide v11.x](https://www.physics.purdue.edu/xrm/new-users/training/Xradia_Versa_Users_Guide_v11x_510.pdf) (local confirmation required).
[ZEISS two-stage magnification technical note](https://asset-downloads.zeiss.com/catalogs/download/mic/02632a56-567c-4a98-b8a7-e9bd31e3f5cc/APAC-only_EN_wp_expanding_boundaries_3D_X-ray_Versa_515.pdf).
