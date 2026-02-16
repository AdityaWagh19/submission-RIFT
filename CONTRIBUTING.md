# Contributing to Algorand Fintech Boilerplate

Thank you for your interest in contributing! This boilerplate is designed to help developers quickly build Algorand dApps.

## How to Contribute

### Reporting Issues
- Use GitHub Issues to report bugs or suggest features
- Include steps to reproduce for bugs
- For feature requests, explain the use case

### Pull Requests
We welcome PRs for:
- Bug fixes
- Documentation improvements
- New example contracts (in `backend/contracts/`)
- Frontend module improvements (wallet, transaction, UI utilities)

**Please do NOT submit PRs that:**
- Change the core architecture without discussion
- Add unnecessary dependencies
- Include secrets or API keys

### Development Setup
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes
4. Test thoroughly (backend + frontend)
5. Commit with clear messages
6. Push and create a PR

### Code Style
- **Python**: Follow PEP 8
- **JavaScript**: Use ES6+ modules, clear function names
- **Comments**: Explain *why*, not *what*

## Adding Example Contracts

If you want to contribute an example contract:

1. Create `backend/contracts/your_contract/contract.py`
2. Include metadata constants (CONTRACT_NAME, DESCRIPTION, etc.)
3. Compile it: `python -m contracts.compile your_contract`
4. Add a README in the contract folder explaining the use case
5. Optionally: Add a frontend example in `examples/your_contract/`

## Questions?

Open a GitHub Discussion or Issue. We're here to help!
