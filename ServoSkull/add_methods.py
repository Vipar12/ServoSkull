#!/usr/bin/env python3
with open('../cogs/commands.py', 'r') as f:
    content = f.read()

# Find the insertion point - after the army_autocomplete method
insertion_marker = 'return [app_commands.Choice(name=army, value=army) for army in matches]'
marker_idx = content.rfind(insertion_marker)  # Use rfind to get the last one (the army one)

if marker_idx > 0:
    # Find the end of this line
    end_of_line = content.find('\n', marker_idx)
    insertion_point = end_of_line + 1

    new_methods = '''
    @classmethod
    def _normalize_disposition(cls, value: str) -> str:
        return " ".join(value.strip().lower().split())

    @classmethod
    def _disposition_lookup(cls) -> dict[str, str]:
        return {cls._normalize_disposition(name): name for name in cls.ALLOWED_DISPOSITIONS}

    def _validate_disposition(self, disposition: str) -> Optional[str]:
        lookup = self._disposition_lookup()
        return lookup.get(self._normalize_disposition(disposition))

    async def disposition_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        current_norm = self._normalize_disposition(current)

        starts_with = []
        contains = []

        for disposition in self.ALLOWED_DISPOSITIONS:
            disp_norm = self._normalize_disposition(disposition)

            if not current_norm:
                starts_with.append(disposition)
            elif disp_norm.startswith(current_norm):
                starts_with.append(disposition)
            elif current_norm in disp_norm:
                contains.append(disposition)

        matches = (starts_with + contains)[:25]
        return [app_commands.Choice(name=disp, value=disp) for disp in matches]

    def _format_date_display(self, date_str: str) -> str:
        """Convert ISO format (YYYY-MM-DD) to display format (DD/MM/YYYY)"""
        try:
            dt = datetime.datetime.fromisoformat(date_str)
            return dt.strftime("%d/%m/%Y")
        except Exception:
            return date_str

'''

    new_content = content[:insertion_point] + new_methods + content[insertion_point:]

    with open('../cogs/commands.py', 'w') as f:
        f.write(new_content)

    print("Added disposition methods!")
else:
    print("Could not find insertion point")
