from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as ticker
import pandas as pd
import tomllib

plt.rc('font', size=12)

CHEMIN_CONFIG = Path("config/releves_de_compte.toml")

MOIS_FR = {1: "Janvier", 2: "Février", 3: "Mars", 4: "Avril",
           5: "Mai", 6: "Juin", 7: "Juillet", 8: "Août",
           9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre"}

def main():
    config = load_config()

    df = pd.read_excel(
        config["source"]["chemin"], **config["source"]["read_excel_kwargs"]
    ).sort_index()

    chemin = Path(config["destination"]["chemin"])
    chemin.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(chemin)


    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=config["image"]["figsize"],
                                   sharex=True)

    plot_debits_credits(ax1, df, config)
    plot_situation(ax2, df, config)
    setup_ax(ax1)
    setup_ax(ax2)

    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(config["image"]["chemin"], **config["image"]["kwargs"])
    plt.show()

def setup_ax(ax):
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_minor_locator(mdates.MonthLocator())
    ax.grid(True, which="major", axis="x", linewidth=1.5, color="gray")
    ax.grid(True, which="minor", axis="x", alpha=0.3)
    ax.grid(True, axis="y", alpha=0.3)
    ax.yaxis.set_major_formatter(
        ticker.FuncFormatter(lambda x, p: f"{x:,.0f}".replace(",", " ")))

def plot_debits_credits(ax, df, config):
    x = df.index.values
    ax.plot(
        x, df[config["source"]["colonne_debit"]],
        label=config["source"]["colonne_debit"],
        color=config["image"]["couleur_negatif"]
    )
    ax.plot(
        x, df[config["source"]["colonne_credit"]],
        label=config["source"]["colonne_credit"],
        color=config["image"]["couleur_positif"]
    )
    ax.fill_between(
        x, df[config["source"]["colonne_debit"]],
        df[config["source"]["colonne_credit"]],
        where=(df[config["source"]["colonne_credit"]] >=
               df[config["source"]["colonne_debit"]]),
        interpolate=True, alpha=0.3,
        color=config["image"]["couleur_positif"], label="Excédent"
    )
    ax.fill_between(
        x, df[config["source"]["colonne_debit"]],
        df[config["source"]["colonne_credit"]],
        where=(df[config["source"]["colonne_credit"]] <
               df[config["source"]["colonne_debit"]]),
        interpolate=True, alpha=0.3,
        color=config["image"]["couleur_negatif"], label="Déficit"
    )
    ax.set_ylabel("Montant (€)")
    ax.legend()

def plot_situation(ax, df, config):
    situation = df[config["source"]["colonne_situation"]].dropna()
    colors = situation.map(
        lambda v: config["image"]["couleur_positif"]
        if v >= 0 else config["image"]["couleur_negatif"]
    ).tolist()
    ax.bar(
        situation.index.values, situation,
        width=pd.Timedelta(days=28).value, color=colors
    )

    # Cycle saisonnier
    monthly_mean = situation.groupby(situation.index.month).mean()
    seasonal = pd.Series(situation.index.month.map(monthly_mean).values,
                         index=situation.index)
    ax.plot(seasonal.index.values, seasonal,
            color="black", linewidth=1.5, label="Cycle saisonnier")

    # Annotations min/max
    for idx, label, offset in [(seasonal.idxmin(), "min", (-60, -35)),
                                (seasonal.idxmax(), "max", (10, 10))]:
        val = seasonal[idx]
        ax.plot(idx, val, "v" if label == "min" else "^", color="black")
        ax.annotate(f"{MOIS_FR[idx.month]}: {val:.0f} €",
                    xy=(idx, val), xytext=offset, textcoords="offset points")

    # Double flèche trésorerie de départ
    val_min = seasonal[seasonal.idxmin()]
    val_dec = seasonal[seasonal.index.month == 12].iloc[-1]
    ecart = val_dec - val_min
    ny = 2
    x_fleche = seasonal.idxmin() + pd.DateOffset(years=ny)
    x_dec = seasonal[seasonal.index.month == 12].index[ny]
    ax.plot(x_dec, val_dec, "s", color="black")
    ax.plot(x_fleche, val_min, "v", color="black")
    ax.annotate("",
                xy=(x_fleche - pd.Timedelta(days=35), val_min),
                xytext=(x_fleche - pd.Timedelta(days=35), val_dec),
                arrowprops=dict(arrowstyle="<->", color="black"))
    ax.annotate(f"{ecart:.0f} €",
                xy=(x_fleche, (val_min + val_dec) / 2),
                xytext=(-65, -25), textcoords="offset points", va="center")

    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_ylabel("Situation (€)")
    ax.legend()

def load_config():
    with open(CHEMIN_CONFIG, "rb") as f:
        config = tomllib.load(f)

    return config

if __name__ == "__main__":
    main()
