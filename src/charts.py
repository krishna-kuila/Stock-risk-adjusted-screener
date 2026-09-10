import numpy as np
import pandas as pd
import plotly.graph_objects as go
from src.metrics import compute_drawdown_series


def _apply_dark_theme(fig: go.Figure, height: int = 380) -> go.Figure:
    """Applies a soothing warm dark theme with gentle contrast, muted typography, and fine reference lines."""
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#27272a",
        plot_bgcolor="#18181b",
        height=height,
        margin=dict(l=55, r=20, t=30, b=40),
        font=dict(
            family="Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
            size=12,
            color="#e4e4e7"
        ),
        title=dict(
            font=dict(color="#e4e4e7", size=13, weight="bold")
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0.0,
            bgcolor="#18181b",
            bordercolor="#3f3f46",
            borderwidth=1,
            font=dict(size=11, color="#e4e4e7")
        ),
        xaxis=dict(
            fixedrange=True,
            showgrid=True,
            gridcolor="#27272a",
            gridwidth=1,
            linecolor="#3f3f46",
            linewidth=1.2,
            tickfont=dict(color="#a1a1aa", size=11),
            title=dict(font=dict(color="#e4e4e7", size=12, weight="bold")),
            zeroline=True,
            zerolinecolor="#3f3f46",
            zerolinewidth=0.8
        ),
        yaxis=dict(
            fixedrange=True,
            showgrid=True,
            gridcolor="#27272a",
            gridwidth=1,
            linecolor="#3f3f46",
            linewidth=1.2,
            tickfont=dict(color="#a1a1aa", size=11),
            title=dict(font=dict(color="#e4e4e7", size=12, weight="bold")),
            zeroline=True,
            zerolinecolor="#3f3f46",
            zerolinewidth=0.8
        ),
        hoverlabel=dict(
            bgcolor="#18181b",
            font_size=12,
            font_color="#e4e4e7",
            bordercolor="#3f3f46",
            font_family="Inter, sans-serif"
        )
    )
    return fig

# Alias for backwards compatibility
_apply_white_theme = _apply_dark_theme


def plot_cumulative_growth(selected: list[str], returns_df: pd.DataFrame) -> go.Figure:
    """Plots normalized growth (% total return) comparison for selected tickers."""
    fig = go.Figure()
    for t in selected:
        if t in returns_df.columns:
            s_ret = returns_df[t].dropna().sort_index()
            cum_ret = ((1.0 + s_ret).cumprod() - 1.0) * 100.0
            last_ret = cum_ret.iloc[-1] if not cum_ret.empty else 0.0
            fig.add_trace(go.Scatter(
                x=pd.to_datetime(cum_ret.index),
                y=cum_ret,
                mode="lines",
                name=f"{t} ({last_ret:+.1f}%)",
                line=dict(width=2.0),
                hovertemplate=f"<b>{t}</b><br>Date: %{{x|%b %d, %Y}}<br>Total Return: %{{y:+.2f}}%<extra></extra>"
            ))

    fig.add_hline(y=0, line_color="#52525b", line_width=1.0, line_dash="solid")
    fig.update_layout(
        yaxis=dict(
            title=dict(text="Total Return (%)", font=dict(color="#e4e4e7", size=12, weight="bold")),
            ticksuffix="%"
        )
    )
    return _apply_dark_theme(fig, height=380)


def plot_drawdown_curves(selected: list[str], returns_df: pd.DataFrame, selected_scores: pd.DataFrame) -> go.Figure:
    """Plots drawdown percentage from peak for selected tickers."""
    fig = go.Figure()
    for t in selected:
        if t in returns_df.columns:
            s_ret = returns_df[t].dropna().sort_index()
            dd = compute_drawdown_series(s_ret) * 100.0
            mdd_val = None
            if selected_scores is not None and not selected_scores.empty and "Ticker" in selected_scores.columns:
                mdd_row = selected_scores.loc[selected_scores["Ticker"] == t, "Max Drawdown"]
                if not mdd_row.empty and pd.notna(mdd_row.values[0]):
                    mdd_val = float(mdd_row.values[0])
            if mdd_val is None:
                mdd_val = float(dd.min() / 100.0) if not dd.empty else 0.0
            mdd_str = f"{mdd_val:.1%}"
            fig.add_trace(go.Scatter(
                x=pd.to_datetime(dd.index),
                y=dd,
                mode="lines",
                name=f"{t} (Worst: {mdd_str})",
                line=dict(width=1.8),
                hovertemplate=f"<b>{t}</b><br>Date: %{{x|%b %d, %Y}}<br>Drawdown: %{{y:.2f}}%<extra></extra>"
            ))

    fig.add_hline(y=0, line_color="#52525b", line_width=1.0, line_dash="solid")
    fig.update_layout(
        yaxis=dict(
            title=dict(text="Drawdown %", font=dict(color="#e4e4e7", size=12, weight="bold")),
            ticksuffix="%"
        )
    )
    return _apply_dark_theme(fig, height=380)


def plot_correlation_matrix(corr_matrix: pd.DataFrame) -> go.Figure:
    """Plots correlation heatmap with distinct, non-white pastel colors and clear text."""
    clean_corr = corr_matrix.fillna(0.0)
    cols = list(clean_corr.columns)
    vals = np.round(clean_corr.values, 2)
    
    # Warm dark palette: soft teal/emerald -> warm amber -> soft coral red
    non_white_colorscale = [
        [0.0, "#34d399"],   # soft emerald (best diversification)
        [0.5, "#fbbf24"],   # warm amber (moderate overlap)
        [1.0, "#f87171"]    # soft coral red (high overlap)
    ]

    fig = go.Figure(data=go.Heatmap(
        z=vals,
        x=cols,
        y=cols,
        colorscale=non_white_colorscale,
        zmin=-0.2,
        zmax=1.0,
        xgap=2,
        ygap=2,
        text=vals,
        texttemplate="%{text:.2f}",
        textfont=dict(size=13, color="#18181b", family="Inter, sans-serif"),
        colorbar=dict(
            title=dict(text="Corr", font=dict(size=11, color="#e4e4e7")),
            len=0.9,
            thickness=14,
            tickfont=dict(size=10, color="#a1a1aa"),
            outlinecolor="#3f3f46",
            outlinewidth=1
        ),
        hovertemplate="<b>%{x}</b> & <b>%{y}</b><br>Correlation: %{z:.2f}<extra></extra>"
    ))
    fig.update_layout(
        yaxis=dict(
            fixedrange=True,
            autorange="reversed",
            tickfont=dict(color="#a1a1aa", size=11)
        ),
        xaxis=dict(
            fixedrange=True,
            tickangle=0,
            tickfont=dict(color="#a1a1aa", size=11)
        )
    )
    return _apply_dark_theme(fig, height=350)


def plot_benchmark_comparison(target_ticker: str, stock_cum: pd.Series, bench_cum: pd.Series, stock_total: float, bench_total: float) -> go.Figure:
    """Plots cumulative return vs Nifty 50 benchmark with solid lines and a delicate 0% line."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=pd.to_datetime(stock_cum.index),
        y=stock_cum,
        mode="lines",
        name=f"{target_ticker} ({stock_total:+.1f}%)",
        line=dict(color="#f59e0b", width=2.2), # Warm amber
        hovertemplate=f"<b>{target_ticker}</b><br>Date: %{{x|%b %d, %Y}}<br>Return: %{{y:+.2f}}%<extra></extra>"
    ))
    fig.add_trace(go.Scatter(
        x=pd.to_datetime(bench_cum.index),
        y=bench_cum,
        mode="lines",
        name=f"Nifty 50 ({bench_total:+.1f}%)",
        line=dict(color="#38bdf8", width=2.2),  # Crisp sky cyan
        hovertemplate="<b>Nifty 50</b><br>Date: %{x|%b %d, %Y}<br>Return: %{y:+.2f}%<extra></extra>"
    ))
    fig.add_hline(y=0, line_color="#52525b", line_width=1.0, line_dash="solid")
    fig.update_layout(
        yaxis=dict(
            title=dict(text="Total Return (%)", font=dict(color="#e4e4e7", size=12, weight="bold")),
            ticksuffix="%"
        )
    )
    return _apply_dark_theme(fig, height=380)


def plot_var_histogram(stock_ret: pd.Series, var_cutoff_pct: float) -> go.Figure:
    """Plots daily return distribution with 95% 1D VaR cutoff line and dark bar outlines."""
    ret_pct = stock_ret * 100
    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=ret_pct,
        nbinsx=40,
        marker=dict(
            color="#f59e0b",
            line=dict(color="#18181b", width=1.0)
        ),
        hovertemplate="Daily Return: %{x:.2f}%<br>Days: %{y}<extra></extra>"
    ))
    fig.add_vline(
        x=var_cutoff_pct,
        line_dash="dash",
        line_color="#ef4444",
        line_width=2.0,
        annotation_text=f"95% VaR Cutoff ({var_cutoff_pct:.2f}%)",
        annotation_position="top left",
        annotation_font=dict(color="#ef4444", size=11)
    )
    fig.update_layout(
        xaxis=dict(
            title=dict(text="Daily Return (%)", font=dict(color="#e4e4e7", size=12, weight="bold")),
            ticksuffix="%"
        ),
        yaxis=dict(
            title=dict(text="Frequency (Days)", font=dict(color="#e4e4e7", size=12, weight="bold"))
        ),
        showlegend=False
    )
    return _apply_dark_theme(fig, height=340)

