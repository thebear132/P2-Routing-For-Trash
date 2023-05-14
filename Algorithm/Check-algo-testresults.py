import pickle
import pandas as pd

# filename = 'BB_algotest'
# filename = 'BB_algotest_meta'

# filename = 'BB_algotest-timelimit'
filename = 'BB_algotest_meta-timelimit'

with open(filename, "rb") as file:
    df_dict = pickle.load(file)

    print(f"\nShowing results from filename: {filename}: \nInputs where:")

    for key in df_dict:
        print(df_dict[key])

# first solution strat (både med solution limit og timelimit - ens resultater ca.):
#   "1" aotumatic og "2" cheapest arc ser lige gode ud. Muligvis fordi "1" vælger "2" i de her scenarier.
#   "3" er nogle gange bedre, men bruger også 1.5 gange så lang tid når antallet af molokker vokser

# meta heurestic (både med solution limit og timelimit):
#   "3" er den klare vinder. Den finder de bedste ruter (ALLE cases) og på kortere tid (ved solution limits) end sim. annealing og
#   Tabu search. "1" automatic er dog meget meget hurtig, men ikke helt så dygtig som de andre.
#   Med timilimit på 120 sekunder, er "3" igen den klare vinder. Google skriver også at den er særligt god til VRP.



# __________________ RESULTAT __________________

# first solution strategy: "1" eller "2". "1" er AUTOMATIC, "2" er PATH_CHEAPEST_ARC.
# local search strategy: "3" GUIDED_LOCAL_SEARCH er konge (også ifølge Google)