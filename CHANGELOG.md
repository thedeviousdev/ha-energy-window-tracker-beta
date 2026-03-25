# Changelog

## [2.3.63](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/compare/v2.3.62...v2.3.63) (2026-03-25)


### Refactoring

* **energy_window_tracker_beta:** remove legacy migration code ([#52](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/52)) ([469f42a](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/469f42a373871973e3ac48362b1942cfcec9829b))

## [2.3.62](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/compare/v2.3.61...v2.3.62) (2026-03-25)


### Features

* improve window flow safety, naming, and time precision ([#8](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/8)) ([3ea1eb1](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/3ea1eb10b56376ca53798f998551ccab7c14fcc7))
* initialize beta integration repository ([a64cf66](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/a64cf669fcab1065b8c6dbfd493593b5d7fb429b))
* **options:** show success modal and return to configure ([529c9c7](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/529c9c70565a9f641395d7c1ed86691dbe320513))
* **sensor:** import_cost, export_credit; fix export_rate in config flatten ([#47](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/47)) ([490b272](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/490b2728c40dd0ecb9ef5ad4fb077332b9672e3d))
* stable source_slot_id, UUID unique_ids, one-time registry migration ([#49](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/49)) ([538a688](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/538a688c6aea71982b6e998fc05b47fa08ec1cda))
* **wf:** 1-based time range keys + wf_entities confirmation ([6b57bb1](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/6b57bb1ec3dad3c3f5c9c080185bb38ecb0b2790))


### Bug Fixes

* **branding:** invert light/dark asset variants ([#30](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/30)) ([2ba42cb](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/2ba42cb99b48227e95087000deb2c2cb4491d9e3))
* **branding:** move logo assets into brand folder ([#26](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/26)) ([f67856f](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/f67856faf159109f2b45568f4878ea9875bbdf71))
* **config-flow:** avoid non-serializable time schema validators ([#16](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/16)) ([c46335b](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/c46335b46d4b0885e31536cc9deaa6dbb4658e64))
* **config-flow:** support new ConfigEntry constructor requirements ([#18](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/18)) ([7340707](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/734070713f94d04c18009421b2b5dd36881152dc))
* **flow:** clear time slots remove ranges (no Optional defaults) ([#45](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/45)) ([a9ae704](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/a9ae704849e8add64285aa07e8c26a97726ce5ee))
* **flow:** correct edit modal title and multi-entity rename behavior ([#36](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/36)) ([a51fb8f](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/a51fb8fa028fa4755a9886ba03066bd17437af46))
* **flow:** dynamic configure title and single source-management form ([#22](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/22)) ([ebc71cc](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/ebc71cc47cae4a7d207a5f34a99b06154b74abbb))
* **flow:** persist import/export rates through edit paths ([#44](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/44)) ([0bcb6f1](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/0bcb6f135a02d6f9934f6f8ee4934329cf8862df))
* **flow:** preserve multi-range values on immediate edit ([#38](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/38)) ([e837183](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/e83718385616ecc012ea468b6aa2e71988b1e23b))
* **flow:** preserve multi-source edits, unique window names, and sensor naming ([#20](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/20)) ([6774fcc](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/6774fccc1e046d63aa86c253a4ab9e13f87047c0))
* **flow:** support import/export rates and empty range removal ([#40](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/40)) ([b5a27e9](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/b5a27e9da2311221094bdd9e1b1d61c778c27dfb))
* **flow:** surface setup failure on initial multi-entity add ([#10](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/10)) ([20bc5a0](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/20bc5a08828c6ab85282f4e72edd17a02dc5f3ad))
* **i18n:** use generic delete label for ranges ([639a0b0](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/639a0b0f19b72d047ecfcff8177faba7d99631ce))
* **options-flow:** keep remaining entities when removing one source ([#32](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/32)) ([a015a90](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/a015a9002fd4dd580ee96943d20b4923d9a80f58))
* **ruff:** organize imports and remove unused ([8d948c9](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/8d948c9d6f6d3d5ae35462b44b7d70e9d523269f))
* **ui:** add explicit per-range delete ([c3f9a6a](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/c3f9a6a3468a19ec4f904a1940a0f414234b93bc))
* **ui:** clear times to remove ranges (no delete checkbox) ([#12](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/12)) ([c82f4a2](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/c82f4a218fab1d4b4994839c5a342a5a71319b54))
* **ui:** clear-to-delete ranges + reduce log noise (schema hotfix) ([#14](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/14)) ([80ffb1b](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/80ffb1b90e7d65340b53bc7d4a330e94c853b301))
* **ui:** improve options flow window/range editing UX ([#6](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/6)) ([69a14de](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/69a14def03bdbf6006ff36e6eb31c5cbf34a5213))
* **ui:** remove delete option and clarify range removal ([aefa67e](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/aefa67eb28a237471b01e1ad242dbf40b38bcc23))
* **ui:** simplify success modal description ([acb4749](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/acb474927136c0bfb9af1c741e6d9a1f3c92281d))
* **ui:** use time selector + updated time labels ([e141ce7](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/e141ce7b18df75937865fb22a78ae796de39a121))
* **ui:** use time selector + updated time labels ([#4](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/4)) ([6d70ed6](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/6d70ed67ac75f283c91d793c7a512f94ac903fb4))


### Refactoring

* **flow:** 1-based time keys + window setup confirmation ([#2](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/2)) ([109cb01](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/109cb01c04d9a705c0c37ece429271bf538d617c))
* **flow:** remove legacy source-first compatibility ([#34](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/34)) ([906b21a](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/906b21aba8d83ae7eb0dea6c953a82c8cabf2706))
* **flow:** remove remaining source-legacy paths ([#42](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/42)) ([2cb0166](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/2cb01663f4f4201a9a595cdd0364e78e6e77276d))
* **flow:** rename window setup steps remove wf references ([f2df84e](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/f2df84eee997f1a048b8797d7f9cc68f25806248))
* **i18n:** consolidate start/end labels ([9ea75d2](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/9ea75d24cc380afd2f0c2bdba14f7349b884dd14))


### Miscellaneous Chores

* **branding:** add light/dark logo assets ([#25](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/25)) ([20a19dd](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/20a19dd018d6c76b0298e7d6164cc9bc2d73b371))
* **main:** release 2.3.39 ([ca05795](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/ca05795465b3d9546c1c8bbc6d02ab502221bee6))
* **main:** release 2.3.39 ([#1](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/1)) ([98e7a85](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/98e7a856f821bda90298975f9cdf65fc4308468e))
* **main:** release 2.3.40 ([2f7d8a6](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/2f7d8a64b3de3662f20f0b789a9d93d838cd3218))
* **main:** release 2.3.40 ([#3](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/3)) ([e6038c9](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/e6038c9a4513edead13bcdef979662888fd1e9a0))
* **main:** release 2.3.41 ([ff07fbd](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/ff07fbdde11d2dc682150e3ea2c00e1d0b3572be))
* **main:** release 2.3.41 ([#5](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/5)) ([1a099b6](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/1a099b69fdeb697bbfd43bd41afa764feb8bbcef))
* **main:** release 2.3.42 ([#7](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/7)) ([11955bb](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/11955bb0c9c369a55a785250320092c676a2e151))
* **main:** release 2.3.43 ([#9](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/9)) ([449d340](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/449d3407a5e589391952356ce80ac09a1b2629c1))
* **main:** release 2.3.44 ([#11](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/11)) ([3602af8](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/3602af8a76f8ed603e6ffd08538bb7b5443ff257))
* **main:** release 2.3.45 ([#13](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/13)) ([2cc9477](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/2cc9477572b5e347cfc97252e50cf06a372d99e4))
* **main:** release 2.3.46 ([#15](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/15)) ([73cc835](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/73cc8358e859399488ec17d25a2dbd98df1399b1))
* **main:** release 2.3.47 ([#17](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/17)) ([624ce09](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/624ce0941bfe0af4d0c8220d820ba713fd066304))
* **main:** release 2.3.48 ([#19](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/19)) ([d8298fc](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/d8298fcf64cb2f1aab2d2c2ee15f8bcf5c7c00ed))
* **main:** release 2.3.49 ([#21](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/21)) ([bfce2ba](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/bfce2ba4a3d6eaa232c419340f42e9d1e279d2e5))
* **main:** release 2.3.50 ([#23](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/23)) ([5cbcb07](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/5cbcb07e7ccba4e131f7f7be144b983731a4c527))
* **main:** release 2.3.51 ([#27](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/27)) ([36309e2](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/36309e2e40b1371f18e181de8e51669d57e25b8d))
* **main:** release 2.3.52 ([#31](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/31)) ([546cdb2](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/546cdb23f9af7748adec382c19b35f9f33535d36))
* **main:** release 2.3.53 ([#33](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/33)) ([bbf5d3c](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/bbf5d3cfd2de5bec95c8895d2e532b8deeeeca98))
* **main:** release 2.3.54 ([#35](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/35)) ([a65b00c](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/a65b00ca9977b6bde70a746727b5c8613a11bd0c))
* **main:** release 2.3.55 ([#37](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/37)) ([963d9bb](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/963d9bbdc5142ed734b8a40e8d9bb95825adfd09))
* **main:** release 2.3.56 ([#39](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/39)) ([070da70](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/070da704c5392d3f117c056965a154db9a1b46bf))
* **main:** release 2.3.57 ([#41](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/41)) ([e6ac079](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/e6ac07975778bddcb9de4c1375f33f3e88679c46))
* **main:** release 2.3.58 ([#43](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/43)) ([a5c9fc7](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/a5c9fc70b50aee237259bbf01d134f9ece84608f))
* **main:** release 2.3.59 ([#46](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/46)) ([63efe81](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/63efe8133c7707f25e9ff906e7d943b5f5e2aa76))
* **main:** release 2.3.60 ([#48](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/48)) ([34beed7](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/34beed75ec92a32edbe318c2d6808e972b958ded))
* **main:** release 2.3.61 ([#50](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/50)) ([484b2b8](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/484b2b8723f1256851ded8c24ddee872a1922cdd))
* mirror project tooling and release automation ([78440f3](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/78440f3a72d93c4af921dbf65c85365242e6b6b8))

## [2.3.61](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/compare/v2.3.60...v2.3.61) (2026-03-25)


### Features

* stable source_slot_id, UUID unique_ids, one-time registry migration ([#49](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/49)) ([538a688](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/538a688c6aea71982b6e998fc05b47fa08ec1cda))

## [2.3.60](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/compare/v2.3.59...v2.3.60) (2026-03-24)


### Features

* **sensor:** import_cost, export_credit; fix export_rate in config flatten ([#47](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/47)) ([490b272](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/490b2728c40dd0ecb9ef5ad4fb077332b9672e3d))

## [2.3.59](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/compare/v2.3.58...v2.3.59) (2026-03-24)


### Bug Fixes

* **flow:** clear time slots remove ranges (no Optional defaults) ([#45](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/45)) ([a9ae704](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/a9ae704849e8add64285aa07e8c26a97726ce5ee))

## [2.3.58](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/compare/v2.3.57...v2.3.58) (2026-03-24)


### Bug Fixes

* **flow:** persist import/export rates through edit paths ([#44](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/44)) ([0bcb6f1](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/0bcb6f135a02d6f9934f6f8ee4934329cf8862df))


### Refactoring

* **flow:** remove remaining source-legacy paths ([#42](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/42)) ([2cb0166](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/2cb01663f4f4201a9a595cdd0364e78e6e77276d))

## [2.3.57](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/compare/v2.3.56...v2.3.57) (2026-03-24)


### Bug Fixes

* **flow:** support import/export rates and empty range removal ([#40](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/40)) ([b5a27e9](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/b5a27e9da2311221094bdd9e1b1d61c778c27dfb))

## [2.3.56](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/compare/v2.3.55...v2.3.56) (2026-03-24)


### Bug Fixes

* **flow:** preserve multi-range values on immediate edit ([#38](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/38)) ([e837183](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/e83718385616ecc012ea468b6aa2e71988b1e23b))

## [2.3.55](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/compare/v2.3.54...v2.3.55) (2026-03-24)


### Bug Fixes

* **flow:** correct edit modal title and multi-entity rename behavior ([#36](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/36)) ([a51fb8f](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/a51fb8fa028fa4755a9886ba03066bd17437af46))

## [2.3.54](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/compare/v2.3.53...v2.3.54) (2026-03-24)


### Refactoring

* **flow:** remove legacy source-first compatibility ([#34](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/34)) ([906b21a](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/906b21aba8d83ae7eb0dea6c953a82c8cabf2706))

## [2.3.53](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/compare/v2.3.52...v2.3.53) (2026-03-24)


### Bug Fixes

* **options-flow:** keep remaining entities when removing one source ([#32](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/32)) ([a015a90](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/a015a9002fd4dd580ee96943d20b4923d9a80f58))

## [2.3.52](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/compare/v2.3.51...v2.3.52) (2026-03-24)


### Bug Fixes

* **branding:** invert light/dark asset variants ([#30](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/30)) ([2ba42cb](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/2ba42cb99b48227e95087000deb2c2cb4491d9e3))

## [2.3.51](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/compare/v2.3.50...v2.3.51) (2026-03-24)


### Bug Fixes

* **branding:** move logo assets into brand folder ([#26](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/26)) ([f67856f](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/f67856faf159109f2b45568f4878ea9875bbdf71))

## [2.3.50](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/compare/v2.3.49...v2.3.50) (2026-03-24)


### Bug Fixes

* **flow:** dynamic configure title and single source-management form ([#22](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/22)) ([ebc71cc](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/ebc71cc47cae4a7d207a5f34a99b06154b74abbb))


### Miscellaneous Chores

* **branding:** add light/dark logo assets ([#25](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/25)) ([20a19dd](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/20a19dd018d6c76b0298e7d6164cc9bc2d73b371))

## [2.3.49](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/compare/v2.3.48...v2.3.49) (2026-03-24)


### Bug Fixes

* **flow:** preserve multi-source edits, unique window names, and sensor naming ([#20](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/20)) ([6774fcc](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/6774fccc1e046d63aa86c253a4ab9e13f87047c0))

## [2.3.48](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/compare/v2.3.47...v2.3.48) (2026-03-24)


### Bug Fixes

* **config-flow:** support new ConfigEntry constructor requirements ([#18](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/18)) ([7340707](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/734070713f94d04c18009421b2b5dd36881152dc))

## [2.3.47](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/compare/v2.3.46...v2.3.47) (2026-03-24)


### Bug Fixes

* **config-flow:** avoid non-serializable time schema validators ([#16](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/16)) ([c46335b](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/c46335b46d4b0885e31536cc9deaa6dbb4658e64))

## [2.3.46](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/compare/v2.3.45...v2.3.46) (2026-03-23)


### Bug Fixes

* **ui:** clear-to-delete ranges + reduce log noise (schema hotfix) ([#14](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/14)) ([80ffb1b](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/80ffb1b90e7d65340b53bc7d4a330e94c853b301))

## [2.3.45](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/compare/v2.3.44...v2.3.45) (2026-03-23)


### Bug Fixes

* **ui:** clear times to remove ranges (no delete checkbox) ([#12](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/12)) ([c82f4a2](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/c82f4a218fab1d4b4994839c5a342a5a71319b54))

## [2.3.44](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/compare/v2.3.43...v2.3.44) (2026-03-23)


### Bug Fixes

* **flow:** surface setup failure on initial multi-entity add ([#10](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/10)) ([20bc5a0](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/20bc5a08828c6ab85282f4e72edd17a02dc5f3ad))

## [2.3.43](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/compare/v2.3.42...v2.3.43) (2026-03-23)


### Features

* improve window flow safety, naming, and time precision ([#8](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/8)) ([3ea1eb1](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/3ea1eb10b56376ca53798f998551ccab7c14fcc7))

## [2.3.42](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/compare/v2.3.41...v2.3.42) (2026-03-23)


### Features

* **options:** show success modal and return to configure ([529c9c7](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/529c9c70565a9f641395d7c1ed86691dbe320513))


### Bug Fixes

* **i18n:** use generic delete label for ranges ([639a0b0](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/639a0b0f19b72d047ecfcff8177faba7d99631ce))
* **ui:** improve options flow window/range editing UX ([#6](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/6)) ([69a14de](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/69a14def03bdbf6006ff36e6eb31c5cbf34a5213))
* **ui:** simplify success modal description ([acb4749](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/acb474927136c0bfb9af1c741e6d9a1f3c92281d))

## [2.3.41](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/compare/v2.3.40...v2.3.41) (2026-03-23)


### Bug Fixes

* **ui:** add explicit per-range delete ([c3f9a6a](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/c3f9a6a3468a19ec4f904a1940a0f414234b93bc))
* **ui:** remove delete option and clarify range removal ([aefa67e](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/aefa67eb28a237471b01e1ad242dbf40b38bcc23))
* **ui:** use time selector + updated time labels ([e141ce7](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/e141ce7b18df75937865fb22a78ae796de39a121))
* **ui:** use time selector + updated time labels ([#4](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/4)) ([6d70ed6](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/6d70ed67ac75f283c91d793c7a512f94ac903fb4))


### Refactoring

* **i18n:** consolidate start/end labels ([9ea75d2](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/9ea75d24cc380afd2f0c2bdba14f7349b884dd14))

## [2.3.40](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/compare/v2.3.39...v2.3.40) (2026-03-23)


### Features

* **wf:** 1-based time range keys + wf_entities confirmation ([6b57bb1](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/6b57bb1ec3dad3c3f5c9c080185bb38ecb0b2790))


### Bug Fixes

* **ruff:** organize imports and remove unused ([8d948c9](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/8d948c9d6f6d3d5ae35462b44b7d70e9d523269f))


### Refactoring

* **flow:** 1-based time keys + window setup confirmation ([#2](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues/2)) ([109cb01](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/109cb01c04d9a705c0c37ece429271bf538d617c))
* **flow:** rename window setup steps remove wf references ([f2df84e](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/f2df84eee997f1a048b8797d7f9cc68f25806248))

## [2.3.39](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/compare/v2.3.38...v2.3.39) (2026-03-23)


### Features

* initialize beta integration repository ([a64cf66](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/a64cf669fcab1065b8c6dbfd493593b5d7fb429b))


### Miscellaneous Chores

* mirror project tooling and release automation ([78440f3](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/commit/78440f3a72d93c4af921dbf65c85365242e6b6b8))
