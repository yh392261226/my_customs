#!/usr/bin/env ruby
# frozen_string_literal: true

require 'optparse'
require 'set'
require 'English'

opts = { panes: :visible }
op = OptionParser.new do |o|
  o.banner = "usage: #{$PROGRAM_NAME} [OPTIONS]"
  o.separator ''
  o.on('-A', '--all', 'All panes') { |_v| opts[:panes] = :all }
  o.on('-a', '--all-but-current',
       'All panes but the active one')          { |_v| opts[:panes] = :others }
  o.on('-s NUM', '--scroll NUM', 'Scroll back') { |v| opts[:scroll] = v }
  o.on('-p STR', '--prefix STR', 'Prefix')      { |v| opts[:prefix] = v }
  o.on('-m NUM', '--min NUM', 'Minimum length') { |v| opts[:min] = v.to_i }
  o.separator ''
  o.on('-h', '--help', 'Show this message') do
    puts o
    exit
  end
  o.separator ''
end

begin
  op.parse!
rescue OptionParser::InvalidOption => x
  warn x
  warn op
  exit 1
end

def list_panes(cond)
  command =
    %q(tmux list-panes -a -F '#{window_active}#{pane_active} #{pane_id}')
  `#{command}`.split($INPUT_RECORD_SEPARATOR).map(&:split).select do |pair|
    status = pair.first
    case cond
    when :all     then true
    when :visible then status =~ /^1/
    when :others  then status !~ /^11/
    end
  end.map(&:last)
end

system 'tmux capture-pane -p &> /dev/null'
if $CHILD_STATUS.exitstatus.zero?
  def capture_pane(pane_id, scroll)
    `tmux capture-pane #{"-S -#{scroll}" if scroll} -t #{pane_id} -p`
  end
else
  def capture_pane(pane_id, scroll)
    `tmux capture-pane #{"-S -#{scroll}" if scroll} -t #{pane_id} &&
     tmux show-buffer && tmux delete-buffer`
  end
end

def tokenize(str, prefix, min)
  set = Set.new
  set.merge(chunks = str.split(/\s+/))
  set.merge(_strip_chunks = chunks.map { |t| t.gsub(/^\W+|\W+$/, '') })
  set.merge(_lines = str.split($INPUT_RECORD_SEPARATOR).map(&:strip))
  set.merge(_words = str.gsub(/\W/, ' ').split(/\s+/))

  prefix &&= /^#{Regexp.escape prefix}/
  if prefix && min
    set.select { |t| t =~ prefix && t.length >= min }
  elsif prefix
    set.select { |t| t =~ prefix }
  elsif min
    set.select { |t| t.length >= min }
  else
    set
  end
rescue StandardError
  []
end

tokens = list_panes(opts[:panes]).inject(Set.new) do |set, pane_id|
  tokens = tokenize(capture_pane(pane_id, opts[:scroll]),
                    opts[:prefix], opts[:min])
  set.merge tokens
end
puts tokens.to_a
