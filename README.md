# Metabolic Ninja

![master Branch](https://img.shields.io/badge/branch-master-blue.svg)
[![master Build Status](https://travis-ci.org/DD-DeCaF/metabolic-ninja.svg?branch=master)](https://travis-ci.org/DD-DeCaF/metabolic-ninja)
[![master Codecov](https://codecov.io/gh/DD-DeCaF/metabolic-ninja/branch/master/graph/badge.svg)](https://codecov.io/gh/DD-DeCaF/metabolic-ninja/branch/master)
[![master Requirements Status](https://requires.io/github/DD-DeCaF/metabolic-ninja/requirements.svg?branch=master)](https://requires.io/github/DD-DeCaF/metabolic-ninja/requirements/?branch=master)

![devel Branch](https://img.shields.io/badge/branch-devel-blue.svg)
[![devel Build Status](https://travis-ci.org/DD-DeCaF/metabolic-ninja.svg?branch=devel)](https://travis-ci.org/DD-DeCaF/metabolic-ninja)
[![devel Codecov](https://codecov.io/gh/DD-DeCaF/metabolic-ninja/branch/devel/graph/badge.svg)](https://codecov.io/gh/DD-DeCaF/metabolic-ninja/branch/devel)
[![devel Requirements Status](https://requires.io/github/DD-DeCaF/metabolic-ninja/requirements.svg?branch=devel)](https://requires.io/github/DD-DeCaF/metabolic-ninja/requirements/?branch=devel)

## Environment

Specify environment variables in a `.env` file. See `docker-compose.yml` for the  possible variables and their default values.

* `ENVIRONMENT`: Set to either `development` or `production`.
* `SENTRY_DSN` DSN for reporting exceptions to [Sentry](https://docs.sentry.io/clients/python/integrations/flask/).
