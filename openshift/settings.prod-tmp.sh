export TOOLS="devex-von-bc-registries-agent-tools"
export PROJECT_NAMESPACE="devex-bcgov-dap"

export ignore_templates="backup-deploy"

# Used for tmp deployment scripts
export images="postgresql postgresql-oracle-fdw bcreg-x-agent mara schema-spy-with-oracle-jdbc"

# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# Danger, Danger, Will Robinson!
# ----------------------------------------------
# Override environments, since there is only one:
# devex-bcgov-dap-dev
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
export DEPLOYMENT_ENV_NAME="dev"
export DEV="dev"
export TEST="dev"
export PROD="dev"