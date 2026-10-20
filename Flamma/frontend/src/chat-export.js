// Keep the medical references with a chat when it is shared or printed.
export function formatChatExport(chat) {
  return `${chat.title}\n\n` + chat.messages.map(message => {
    const speaker = message.who === 'user' ? 'You' : 'Flamma';
    const timestamp = message.createdAt ? ` · ${new Date(message.createdAt).toLocaleString()}` : '';
    let text = `${speaker}${timestamp}\n${message.text}${message.image ? '\n[Attached photo]' : ''}`;
    const sources = message.treatmentInfo?.sources || [];
    if (sources.length) {
      text += '\n\nCare information sources:\n' + sources.map(source => `${source.title}: ${source.url}${source.source_checked_on ? ` (checked ${source.source_checked_on})` : ''}`).join('\n');
      if (message.treatmentInfo.source_checked_on) text += `\nSources checked: ${message.treatmentInfo.source_checked_on}`;
    }
    return text;
  }).join('\n\n');
}
