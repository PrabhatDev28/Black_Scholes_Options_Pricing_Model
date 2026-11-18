"""
Black-Scholes Options Pricing Model
-----------------------------------
Prices European call and put options and calculates:
  - The Greeks (Delta, Gamma, Vega, Theta, Rho)
  - Implied volatility from a market price
  - A put-call parity check
  - A Monte Carlo check of the formula

Change the settings in the "Settings" cell to experiment.
Not financial advice - this is a learning project.
"""

# %% Imports
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import norm
from scipy.optimize import brentq

# %% Settings
S = 2500.0                 # current stock price
K = 2600.0                 # strike price
T = 0.5                    # time to expiry in years (0.5 = 6 months)
r = 0.07                   # risk-free interest rate per year (7%)
sigma = 0.25               # volatility per year (25%)
q = 0.0                    # dividend yield per year (0 = no dividends)
MARKET_CALL_PRICE = 150.0  # a market price of the call, used to find implied volatility
NUM_SIMULATIONS = 200000   # paths for the Monte Carlo check
SEED = 42

np.random.seed(SEED)


# %% Black-Scholes formula
def d1_d2(S, K, T, r, sigma, q=0.0):
    """The two building blocks of the Black-Scholes formula."""
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    return d1, d2


def bs_price(S, K, T, r, sigma, option="call", q=0.0):
    """Black-Scholes price of a European call or put."""
    d1, d2 = d1_d2(S, K, T, r, sigma, q)
    if option == "call":
        return S * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    return K * np.exp(-r * T) * norm.cdf(-d2) - S * np.exp(-q * T) * norm.cdf(-d1)


call_price = bs_price(S, K, T, r, sigma, "call", q)
put_price = bs_price(S, K, T, r, sigma, "put", q)

print(f"Call price: {call_price:.2f}")
print(f"Put price:  {put_price:.2f}")


# %% The Greeks
def greeks(S, K, T, r, sigma, option="call", q=0.0):
    """Delta, Gamma, Vega (per 1% vol), Theta (per day) and Rho (per 1% rate)."""
    d1, d2 = d1_d2(S, K, T, r, sigma, q)
    pdf_d1 = norm.pdf(d1)
    disc_q, disc_r = np.exp(-q * T), np.exp(-r * T)

    gamma = disc_q * pdf_d1 / (S * sigma * np.sqrt(T))
    vega = S * disc_q * pdf_d1 * np.sqrt(T) / 100
    decay = -S * disc_q * pdf_d1 * sigma / (2 * np.sqrt(T))

    if option == "call":
        delta = disc_q * norm.cdf(d1)
        theta = (decay - r * K * disc_r * norm.cdf(d2) + q * S * disc_q * norm.cdf(d1)) / 365
        rho = K * T * disc_r * norm.cdf(d2) / 100
    else:
        delta = disc_q * (norm.cdf(d1) - 1)
        theta = (decay + r * K * disc_r * norm.cdf(-d2) - q * S * disc_q * norm.cdf(-d1)) / 365
        rho = -K * T * disc_r * norm.cdf(-d2) / 100

    return {"Delta": delta, "Gamma": gamma, "Vega": vega, "Theta": theta, "Rho": rho}


call_greeks = greeks(S, K, T, r, sigma, "call", q)
put_greeks = greeks(S, K, T, r, sigma, "put", q)

summary = pd.DataFrame(
    {"Call": {"Price": call_price, **call_greeks},
     "Put": {"Price": put_price, **put_greeks}}
)
print("\n=== Option prices and Greeks ===")
print(summary.round(4).to_string())

# %% Implied volatility
def implied_volatility(market_price, S, K, T, r, option="call", q=0.0):
    """Find the volatility that makes the Black-Scholes price match the market price."""
    objective = lambda vol: bs_price(S, K, T, r, vol, option, q) - market_price
    return brentq(objective, 1e-4, 5.0)


try:
    implied_vol = implied_volatility(MARKET_CALL_PRICE, S, K, T, r, "call", q)
    print(f"\nMarket call price {MARKET_CALL_PRICE:.2f} -> implied volatility {implied_vol:.1%}")
except ValueError:
    implied_vol = np.nan
    print("\nImplied volatility not found: the market price is outside the possible range.")

# %% Put-call parity check
lhs = call_price - put_price
rhs = S * np.exp(-q * T) - K * np.exp(-r * T)
print(f"\nPut-call parity:  C - P = {lhs:.4f}   |   S*e^(-qT) - K*e^(-rT) = {rhs:.4f}")

# %% Monte Carlo check
Z = np.random.standard_normal(NUM_SIMULATIONS)
final_prices = S * np.exp((r - q - 0.5 * sigma ** 2) * T + sigma * np.sqrt(T) * Z)

mc_call = np.exp(-r * T) * np.maximum(final_prices - K, 0)
mc_put = np.exp(-r * T) * np.maximum(K - final_prices, 0)

print(f"\nMonte Carlo call: {mc_call.mean():.2f} (+/- {mc_call.std() / np.sqrt(NUM_SIMULATIONS):.2f})  |  formula: {call_price:.2f}")
print(f"Monte Carlo put:  {mc_put.mean():.2f} (+/- {mc_put.std() / np.sqrt(NUM_SIMULATIONS):.2f})  |  formula: {put_price:.2f}")

# %% Plots
fig, axes = plt.subplots(2, 2, figsize=(15, 11))
ax1, ax2, ax3, ax4 = axes.ravel()
spots = np.linspace(0.6 * S, 1.4 * S, 200)

# 1) Option value vs stock price
ax1.plot(spots, bs_price(spots, K, T, r, sigma, "call", q), color="tab:blue", label="Call value today")
ax1.plot(spots, bs_price(spots, K, T, r, sigma, "put", q), color="tab:red", label="Put value today")
ax1.plot(spots, np.maximum(spots - K, 0), "--", color="tab:blue", alpha=0.5, label="Call payoff at expiry")
ax1.plot(spots, np.maximum(K - spots, 0), "--", color="tab:red", alpha=0.5, label="Put payoff at expiry")
ax1.axvline(K, color="gray", linestyle=":", label="Strike")
ax1.set_title("Option Value vs Stock Price")
ax1.set_xlabel("Stock price")
ax1.set_ylabel("Option value")
ax1.legend()

# 2) Delta and Gamma vs stock price
g_call = greeks(spots, K, T, r, sigma, "call", q)
g_put = greeks(spots, K, T, r, sigma, "put", q)
ax2.plot(spots, g_call["Delta"], color="tab:blue", label="Call Delta")
ax2.plot(spots, g_put["Delta"], color="tab:red", label="Put Delta")
ax2.set_xlabel("Stock price")
ax2.set_ylabel("Delta")
ax2b = ax2.twinx()
ax2b.plot(spots, g_call["Gamma"], color="tab:green", linestyle="--", label="Gamma")
ax2b.set_ylabel("Gamma")
lines = ax2.get_lines() + ax2b.get_lines()
ax2.legend(lines, [l.get_label() for l in lines], loc="center left")
ax2.set_title("Delta and Gamma vs Stock Price")

# 3) Heatmap: call price for different stock prices and volatilities
vols = np.linspace(0.10, 0.60, 60)
grid_S, grid_vol = np.meshgrid(spots, vols)
heat = bs_price(grid_S, K, T, r, grid_vol, "call", q)
im = ax3.imshow(heat, origin="lower", aspect="auto", cmap="viridis",
                extent=[spots.min(), spots.max(), vols.min() * 100, vols.max() * 100])
fig.colorbar(im, ax=ax3, label="Call price")
ax3.scatter([S], [sigma * 100], marker="*", color="white", edgecolor="black", s=250, label="Your inputs")
ax3.set_title("Call Price: Stock Price vs Volatility")
ax3.set_xlabel("Stock price")
ax3.set_ylabel("Volatility (%)")
ax3.legend(loc="upper left")

# 4) Time decay
days = np.linspace(T * 365, 1, 200)
for label, spot in [("In the money", K * 1.1), ("At the money", K), ("Out of the money", K * 0.9)]:
    ax4.plot(days, bs_price(spot, K, days / 365, r, sigma, "call", q), label=f"Call, {label}")
ax4.invert_xaxis()
ax4.set_title("Time Decay of a Call Option")
ax4.set_xlabel("Days to expiry")
ax4.set_ylabel("Call value")
ax4.legend()

plt.tight_layout()
plt.savefig("bs_results.png", dpi=150, bbox_inches="tight")
plt.show()
