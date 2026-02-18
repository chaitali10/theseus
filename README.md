<a href="https://livekit.io/">
  <img src="./.github/assets/livekit-mark.png" alt="LiveKit logo" width="100" height="100">
</a>

# Insurance Verification Voice Agent

A voice AI agent built with [LiveKit Agents for Python](https://github.com/livekit/agents) and [LiveKit Cloud](https://cloud.livekit.io/) that assists clinic front-desk staff with insurance verification.

## How it works

Clinic staff use a frontend UI to enter patient information and initiate an insurance verification call. The voice agent handles the verification process and publishes results back to the frontend in real time via LiveKit participant attributes.

### User workflow

1. **Enter patient info** — The staff member enters patient details (name, DOB, insurance provider, member ID, group number) in the frontend form.
2. **Start verification** — The frontend creates a LiveKit room and joins with the patient data set as participant attributes.
3. **Agent verifies** — The voice agent reads the patient info, confirms it with the user, and calls the `verify_insurance` tool to check coverage.
4. **Results appear** — Verification results (eligibility, copay, deductible, coinsurance, etc.) are published as participant attributes. The frontend listens for attribute changes and updates the UI in real time.
5. **Multiple agents** — Each verification runs in its own LiveKit room, so staff can initiate multiple concurrent verifications.

### Frontend integration

The frontend communicates with the agent using **participant attributes**:

**Sending patient data to the agent** — set attributes before connecting:

```javascript
// When connecting to the room, pass patient info as participant attributes
const room = new Room();
await room.connect(url, token, {
  participantAttributes: {
    "patient.name": "Jane Smith",
    "patient.date_of_birth": "03/15/1985",
    "patient.insurance_provider": "Blue Cross Blue Shield",
    "patient.member_id": "BCB123456",
    "patient.group_number": "GRP7890",
  },
});
```

**Receiving verification results** — listen for attribute changes:

```javascript
room.on(RoomEvent.ParticipantAttributesChanged, (changed, participant) => {
  if (participant.isAgent) {
    // Read verification results from the agent's attributes
    const status = participant.attributes["verification.status"];
    const eligible = participant.attributes["verification.eligible"];
    const copay = participant.attributes["verification.copay"];
    const deductible = participant.attributes["verification.deductible"];
    // ... update your UI
  }
});
```

**Agent attribute keys** published by the agent:

| Key | Description |
|-----|-------------|
| `verification.status` | `pending`, `in_progress`, `verified`, `denied`, or `error` |
| `verification.patient_name` | Confirmed patient name |
| `verification.eligible` | `true` or `false` |
| `verification.copay` | Copay amount |
| `verification.deductible` | Deductible amount |
| `verification.deductible_met` | Deductible amount met so far |
| `verification.coinsurance` | Coinsurance split |
| `verification.out_of_pocket_max` | Out-of-pocket maximum |
| `verification.coverage_details` | Coverage summary |
| `verification.effective_date` | Coverage start date |
| `verification.termination_date` | Coverage end date |
| `verification.notes` | Additional notes |

### Features

- Insurance verification voice agent with guided patient data collection
- `verify_insurance` function tool for LLM-driven verification flow
- Real-time result publishing via participant attributes
- Automatic patient data ingestion from frontend attributes
- A voice AI pipeline with [models](https://docs.livekit.io/agents/models) from OpenAI, Cartesia, and AssemblyAI served through LiveKit Cloud
- Eval suite based on the LiveKit Agents [testing & evaluation framework](https://docs.livekit.io/agents/build/testing/)
- [LiveKit Turn Detector](https://docs.livekit.io/agents/build/turns/turn-detector/) for contextually-aware speaker detection, with multilingual support
- [Background voice cancellation](https://docs.livekit.io/home/cloud/noise-cancellation/)
- Integrated [metrics and logging](https://docs.livekit.io/agents/build/metrics/)
- A Dockerfile ready for [production deployment](https://docs.livekit.io/agents/ops/deployment/)

This agent is compatible with any [custom web/mobile frontend](https://docs.livekit.io/agents/start/frontend/) or [SIP-based telephony](https://docs.livekit.io/agents/start/telephony/).

## Coding agents and MCP

This project is designed to work with coding agents like [Cursor](https://www.cursor.com/) and [Claude Code](https://www.anthropic.com/claude-code). 

To get the most out of these tools, install the [LiveKit Docs MCP server](https://docs.livekit.io/mcp).

For Cursor, use this link:

[![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en-US/install-mcp?name=livekit-docs&config=eyJ1cmwiOiJodHRwczovL2RvY3MubGl2ZWtpdC5pby9tY3AifQ%3D%3D)

For Claude Code, run this command:

```
claude mcp add --transport http livekit-docs https://docs.livekit.io/mcp
```

For Codex CLI, use this command to install the server:
```
codex mcp add --url https://docs.livekit.io/mcp livekit-docs
```

For Gemini CLI, use this command to install the server:
```
gemini mcp add --transport http livekit-docs https://docs.livekit.io/mcp
```

The project includes a complete [AGENTS.md](AGENTS.md) file for these assistants. You can modify this file  your needs. To learn more about this file, see [https://agents.md](https://agents.md).

## Dev Setup

Clone the repository and install dependencies to a virtual environment:

```console
cd agent-starter-python
uv sync
```

Sign up for [LiveKit Cloud](https://cloud.livekit.io/) then set up the environment by copying `.env.example` to `.env.local` and filling in the required keys:

- `LIVEKIT_URL`
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`

You can load the LiveKit environment automatically using the [LiveKit CLI](https://docs.livekit.io/home/cli/cli-setup):

```bash
lk cloud auth
lk app env -w -d .env.local
```

## Run the agent

Before your first run, you must download certain models such as [Silero VAD](https://docs.livekit.io/agents/build/turns/vad/) and the [LiveKit turn detector](https://docs.livekit.io/agents/build/turns/turn-detector/):

```console
uv run python src/agent.py download-files
```

Next, run this command to speak to your agent directly in your terminal:

```console
uv run python src/agent.py console
```

To run the agent for use with a frontend or telephony, use the `dev` command:

```console
uv run python src/agent.py dev
```

In production, use the `start` command:

```console
uv run python src/agent.py start
```

## Frontend & Telephony

Get started quickly with our pre-built frontend starter apps, or add telephony support:

| Platform | Link | Description |
|----------|----------|-------------|
| **Web** | [`livekit-examples/agent-starter-react`](https://github.com/livekit-examples/agent-starter-react) | Web voice AI assistant with React & Next.js |
| **iOS/macOS** | [`livekit-examples/agent-starter-swift`](https://github.com/livekit-examples/agent-starter-swift) | Native iOS, macOS, and visionOS voice AI assistant |
| **Flutter** | [`livekit-examples/agent-starter-flutter`](https://github.com/livekit-examples/agent-starter-flutter) | Cross-platform voice AI assistant app |
| **React Native** | [`livekit-examples/voice-assistant-react-native`](https://github.com/livekit-examples/voice-assistant-react-native) | Native mobile app with React Native & Expo |
| **Android** | [`livekit-examples/agent-starter-android`](https://github.com/livekit-examples/agent-starter-android) | Native Android app with Kotlin & Jetpack Compose |
| **Web Embed** | [`livekit-examples/agent-starter-embed`](https://github.com/livekit-examples/agent-starter-embed) | Voice AI widget for any website |
| **Telephony** | [📚 Documentation](https://docs.livekit.io/agents/start/telephony/) | Add inbound or outbound calling to your agent |

For advanced customization, see the [complete frontend guide](https://docs.livekit.io/agents/start/frontend/).

## Tests and evals

This project includes a complete suite of evals, based on the LiveKit Agents [testing & evaluation framework](https://docs.livekit.io/agents/build/testing/). To run them, use `pytest`.

```console
uv run pytest
```

## Using this template repo for your own project

Once you've started your own project based on this repo, you should:

1. **Check in your `uv.lock`**: This file is currently untracked for the template, but you should commit it to your repository for reproducible builds and proper configuration management. (The same applies to `livekit.toml`, if you run your agents in LiveKit Cloud)

2. **Remove the git tracking test**: Delete the "Check files not tracked in git" step from `.github/workflows/tests.yml` since you'll now want this file to be tracked. These are just there for development purposes in the template repo itself.

3. **Add your own repository secrets**: You must [add secrets](https://docs.github.com/en/actions/how-tos/writing-workflows/choosing-what-your-workflow-does/using-secrets-in-github-actions) for `LIVEKIT_URL`, `LIVEKIT_API_KEY`, and `LIVEKIT_API_SECRET` so that the tests can run in CI.

## Deploying to production

This project is production-ready and includes a working `Dockerfile`. To deploy it to LiveKit Cloud or another environment, see the [deploying to production](https://docs.livekit.io/agents/ops/deployment/) guide.

## Self-hosted LiveKit

You can also self-host LiveKit instead of using LiveKit Cloud. See the [self-hosting](https://docs.livekit.io/home/self-hosting/) guide for more information. If you choose to self-host, you'll need to also use [model plugins](https://docs.livekit.io/agents/models/#plugins) instead of LiveKit Inference and will need to remove the [LiveKit Cloud noise cancellation](https://docs.livekit.io/home/cloud/noise-cancellation/) plugin.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
