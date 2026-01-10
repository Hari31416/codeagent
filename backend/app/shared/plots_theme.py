def set_publish_matplotlib_template(mode: str = "light") -> None:
    """Sets the matplotlib template for publication-ready plots."""
    import matplotlib.pyplot as plt

    text_color = "black" if mode == "light" else "white"
    background_color = "white" if mode == "light" else "black"
    grid_color = "#948b72" if mode == "light" else "#666666"

    plt.rcParams.update(
        {
            "font.size": 18,
            "axes.labelcolor": text_color,
            "axes.labelsize": 18,
            "axes.labelweight": "bold",
            "xtick.labelsize": 16,
            "ytick.labelsize": 16,
            "xtick.color": text_color,
            "ytick.color": text_color,
            "axes.grid": True,
            "axes.facecolor": background_color,
            "figure.facecolor": background_color,
            "figure.titlesize": 20,
            "figure.titleweight": "bold",
            "grid.color": grid_color,
            "grid.linewidth": 1,
            "grid.linestyle": "--",
            "axes.edgecolor": text_color,
            "axes.linewidth": 0.5,
            "text.color": text_color,
            "legend.framealpha": 0.8,
            "legend.edgecolor": text_color,
            "legend.facecolor": background_color,
            "legend.labelcolor": text_color,
        }
    )


def set_publish_plotly_template(mode: str = "light") -> None:
    """Sets the Plotly template for publication-ready plots with full color handling."""
    import plotly.graph_objects as go
    import plotly.io as pio

    # --- Color configuration ---
    is_light = mode.lower() == "light"
    text_color = "black" if is_light else "white"
    background_color = "white" if is_light else "#111111"
    grid_color = "#e5e5e5" if is_light else "#333333"
    axis_color = "#444444" if is_light else "#cccccc"
    hover_bg = "rgba(255,255,255,0.9)" if is_light else "rgba(30,30,30,0.9)"
    hover_border = "#bbbbbb" if is_light else "#555555"

    # --- Font setup ---
    font_family = "Times New Roman"

    def get_font_dict(size: int, color: str = text_color) -> dict:
        return dict(
            size=size,
            color=color,
            family=font_family,
        )

    # --- Define template layout ---
    layout = go.Layout(
        font=get_font_dict(16),
        title=dict(font=get_font_dict(24)),
        legend=dict(
            font=get_font_dict(18),
            bgcolor=background_color,
            bordercolor=axis_color,
        ),
        margin=dict(l=80, r=20, t=80, b=80),
        xaxis=dict(
            title=dict(font=get_font_dict(18)),
            tickfont=get_font_dict(16),
            showline=True,
            linecolor=axis_color,
            gridcolor=grid_color,
            zeroline=False,
            automargin=True,
            title_standoff=20,  # push x-title away from ticks/labels
        ),
        yaxis=dict(
            title=dict(font=get_font_dict(18)),
            tickfont=get_font_dict(16),
            showline=True,
            linecolor=axis_color,
            gridcolor=grid_color,
            zeroline=False,
            automargin=True,
            title_standoff=20,
        ),
        plot_bgcolor=background_color,
        paper_bgcolor=background_color,
        hoverlabel=dict(
            font=get_font_dict(14),
            bgcolor=hover_bg,
            bordercolor=hover_border,
        ),
    )

    # --- Apply template globally ---
    pio.templates["publish"] = go.layout.Template(layout=layout)
    pio.templates.default = "publish"
