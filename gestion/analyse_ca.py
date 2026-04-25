from matplotlib.lines import Line2D
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path

plt.rc('font', size=12)

ANNEES = ['2023', '2024', '2025']
RACINE = Path('..')
COL_CA = ['Recettes /marché']
# COL_CA = ['Recettes /marché', ' chèques factures', 'virements factures']
DEBOUCHE_JOUR = {
    'Marché bio de Dol': 2,
    'Pain au marché bio de Dol': 2,
    'Marché de Pontorson': 3,
    'Marché du jeudi à Rocabey': 4,
    'Vente à la ferme': 5,
    'Marché du samedi à Rocabey': 6
}
DEMI_DEBOUCHES = ['Marché bio de Dol', 'Pain au marché bio de Dol']
PARITE_MARCHE_BIO = 1

READ_EXCEL_KWARGS = dict(header=0)

DOSSIER_ORGANISATION_TRAVAIL = Path(
    '..', '..', '..', 'Installation', 'dossier_dja',
    'organisation_travail')
FICHIER_ORGANISATION_TRAVAIL = 'emploi_du_temps_prévisionnel.ods'
FEUILLE_ORGANISATION_TRAVAIL = 'Coûts de commercialisation'
COL_COUT = 'Coût de commercialisation (€)'

COLORS = plt.rcParams['axes.prop_cycle'].by_key()['color']
LINESTYLES = {
    '2023': ':',
    '2024': '--',
    '2025': '-',
}
FIGXSCALE =  1.5
LINEWIDTH = 2
SAVEFIG_KWARGS = dict(dpi=300, bbox_inches='tight')
FIG_DOSSIER = Path('figures')

def main():
    data = []
    for annee in ANNEES:
        dossier = Path(RACINE, annee)
        fichier = f"chiffre d'affaire {annee}.ods"
        chemin = Path(dossier, fichier)
        df_annee = pd.read_excel(chemin, **READ_EXCEL_KWARGS)
        df_annee = df_annee.loc[~df_annee['Année'].isnull()]
        date_dict = {
            'year': df_annee['Année'],
            'month': df_annee['Mois'],
            'day': df_annee['Jour']
        }
        index = pd.to_datetime(date_dict)
        df_annee = df_annee.set_index(index)
        df_annee['CA'] = df_annee[COL_CA].sum('columns')
        data.append(df_annee)
    df = pd.concat(data)
    calendrier = df.index.isocalendar()

    df_debouches = pd.DataFrame(index=df.index, dtype=float)
    for debouche, jour in DEBOUCHE_JOUR.items():
        index_debouche = calendrier['day'] == jour
        if debouche == 'Marché bio de Dol':
            index_debouche &= ((calendrier['week'] % 2) ==
                               PARITE_MARCHE_BIO)
        elif debouche == 'Pain au marché bio de Dol':
            index_debouche &= ((calendrier['week'] % 2) !=
                               PARITE_MARCHE_BIO)
        df_debouches[debouche] = df['CA'].where(index_debouche)
    df_debouches_par_semaine = df_debouches.groupby(
        [calendrier['year'], calendrier['week']]).sum()
    df_debouches_par_bisemaine = df_debouches_par_semaine.rolling(
        2, step=2).mean()
    df_debouches_par_bisemaine[DEMI_DEBOUCHES] *= 2

    figsize = plt.rcParams['figure.figsize']
    figsize[0] = figsize[0] * FIGXSCALE
    fig, ax = plt.subplots(figsize=figsize)
    for annee in ANNEES: 
        df_debouches_par_bisemaine.loc[int(annee)].plot(
            ax=ax, color=COLORS, linestyle=LINESTYLES[annee],
            linewidth=LINEWIDTH, legend=False)
    ax.set_xlabel("Semaine de l'année")
    ax.set_ylabel("CA sur 2 semaines par débouché (€)")
    ylim = (0, df_debouches_par_bisemaine.max().max() * 1.05)
    ax.set_ylim(ylim)

    # Legendes
    box = ax.get_position()
    ax.set_position([box.x0, box.y0, box.width / FIGXSCALE, box.height])
    debouches = df_debouches_par_bisemaine.columns
    debouche_handles = [
        Line2D([0], [0], color=color, lw=LINEWIDTH, label=col)
        for col, color in zip(debouches, COLORS)
    ]
    legend_debouches = ax.legend(
        handles=debouche_handles,
        title="Débouché",
        loc="upper left",
        bbox_to_anchor=(1, 1)
    )
    annee_handles = [
        Line2D([0], [0], color="k", lw=LINEWIDTH, label=annee,
               linestyle=LINESTYLES[annee])
        for annee in ANNEES
    ]
    legend_annees = ax.legend(
        handles=annee_handles,
        title="Année",
        loc="lower left",
        bbox_to_anchor=(1, 0.15)
    )
    ax.add_artist(legend_debouches)
    ax.grid(True)

    fig_fichier = f'ca_par_debouche_{'_'.join(ANNEES)}.png'
    FIG_DOSSIER.mkdir(exist_ok=True)
    fig_chemin = Path(FIG_DOSSIER, fig_fichier)
    fig.savefig(fig_chemin, **SAVEFIG_KWARGS)

    fig, ax = plt.subplots()
    i_annees = [int(annee) for annee in ANNEES]
    df_annuel = df_debouches_par_bisemaine.groupby('year').sum().loc[
        i_annees] / 1000
    df_annuel.T.plot(ax=ax, kind='bar')
    ax.set_ylabel("CA sur l'année par débouché (k€)")
    ylim_annuel = (0, df_annuel.max().max() * 1.05)
    ax.set_ylim(ylim_annuel)
    plt.xticks(rotation=45)
    plt.tight_layout()
    ax.grid(True)

    fig_fichier = f'ca_annuel_par_debouche_{'_'.join(ANNEES)}.png'
    FIG_DOSSIER.mkdir(exist_ok=True)
    fig_chemin = Path(FIG_DOSSIER, fig_fichier)
    fig.savefig(fig_chemin, **SAVEFIG_KWARGS)

    chemin_organisation_travail = Path(DOSSIER_ORGANISATION_TRAVAIL,
                                       FICHIER_ORGANISATION_TRAVAIL)
    df_orga = pd.read_excel(
        chemin_organisation_travail,
        sheet_name=FEUILLE_ORGANISATION_TRAVAIL,
        header=0, index_col=0, nrows=7)
    s_cout = df_orga[COL_COUT]

    for k, (debouche, df_deb) in enumerate(
            df_debouches_par_bisemaine.items()):
        fig, ax = plt.subplots()
        moy = df_deb.groupby('week').mean()
        cout = s_cout.loc[debouche] * 2
        for annee in ANNEES: 
            df_deb.loc[int(annee)].plot(
                ax=ax, color=COLORS[k], linestyle=LINESTYLES[annee],
                linewidth=LINEWIDTH, label=annee)
        xlim = ax.get_xlim()
        moy.plot(ax=ax, color=COLORS[k], linestyle='-',
                 linewidth=1, label='Moyenne')
        ax.hlines([cout], *xlim, color='k', linestyle='-',
                  linewidth=1, label=COL_COUT)
        ax.set_ylim(ylim)
        ax.set_xlabel("Semaine de l'année")
        ax.set_ylabel(f"CA sur 2 semaines - {debouche} (€)")
        ax.grid(True)
        ax.legend()

        fig_fichier = f'ca_{debouche}_{'_'.join(ANNEES)}.png'
        FIG_DOSSIER.mkdir(exist_ok=True)
        fig_chemin = Path(FIG_DOSSIER, fig_fichier)
        fig.savefig(fig_chemin, **SAVEFIG_KWARGS)


    plt.show(block=False)
        
    return

if __name__ == "__main__":
    main()
