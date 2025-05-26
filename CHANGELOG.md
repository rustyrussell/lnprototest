# v0.0.5

## Fixed
- Correct reorg issue in the ln helper function ([commit](https://github.com/rustyrussell/lnprototest/commit/ad3129d4dad14e98a0b3f1210d349d2b6503ce53)). @vincenzopalazzo 21-09-2023
- Correct error check for expected errors ([commit](https://github.com/rustyrussell/lnprototest/commit/3dafe1d0b010aa0fb98b545a3a0fef6985153087)). @vincenzopalazzo 15-07-2023
- runner_features added in runner.py and applied in ln_spec_utils.py ([commit](https://github.com/rustyrussell/lnprototest/commit/0dc5dddbb209bd8edf4d2a93973b72882724b865)). @Psycho-Pirate 24-06-2023
- Modified Reestablish test to use new code and used stash ([commit](https://github.com/rustyrussell/lnprototest/commit/6cd0791f961d7c8d596d45c9725a463e5f52eed4)). @Psycho-Pirate 19-06-2023
- resolve the number callback in Block event ([commit](https://github.com/rustyrussell/lnprototest/commit/7ff8d9f33253031ff83bc9aed5ff1b63bd42bf95)). @vincenzopalazzo 06-06-2023

## Added
- Allowing the option to skip the creation of the wallet in bitcoind ([commit](https://github.com/rustyrussell/lnprototest/commit/45711defc89161b8d3efcae747000ae4fb2fd36d)). @vincenzopalazzo 27-07-2023
- Open channel helper ignores announcement signatures ([commit](https://github.com/rustyrussell/lnprototest/commit/ba32816e3291055e7f1eeff01f872f8a3359f66b)). @vincenzopalazzo 16-06-2023
- Support the Drop of the --developer flag at runtime (cln: specify --developer if supported. rustyrussell/lnprototest#106). @rustyrussell


# v0.0.4

## Fixed
- Grab the feature from the init message if it is not specified ([commit](https://github.com/rustyrussell/lnprototest/commit/e2005d731bacf4fffaf4fe92cc96b1d241bde7f8)). @vincenzopalazzo 03-06-2023
- pass the timeout when we are waiting a node to start ([commit](https://github.com/rustyrussell/lnprototest/commit/9b4a0c1521eddee3f1c90aae6bab1aac120c4cba)). @vincenzopalazzo 01-06-2023
- import inside the library some useful utils ([commit](https://github.com/rustyrussell/lnprototest/commit/554659fbdce8376f9f200e98a05f44b3b5c0582c)). @vincenzopalazzo 01-06-2023

## Added
- Enable stashing of expected messages ([commit](https://github.com/rustyrussell/lnprototest/commit/50d72b1f8b08c3d973c8252f3be3c28812247404)). @vincenzopalazzo 01-06-2023
