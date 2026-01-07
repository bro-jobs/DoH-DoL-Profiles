using System;
using ff14bot;
using ff14bot.Managers;
using LlamaLibrary.Memory;
using LlamaLibrary.Utilities;
namespace LlamaLibrary.RemoteAgents;
public class AgentSharlayanCraftworksSupply : AgentInterface<AgentSharlayanCraftworksSupply>, IAgent
{
    public IntPtr RegisteredVtable => AgentSharlayanCraftworksSupplyOffsets.Vtable;
    protected AgentSharlayanCraftworksSupply(IntPtr pointer) : base(pointer)
    {
    }

    public void HandIn(BagSlot slot)
    {
        var instance = Pointer + 0x28;
        var vtable = Core.Memory.Read<IntPtr>(instance);
        var handInFunc = Core.Memory.Read<IntPtr>(vtable); // vtable[0]
        
        Core.Memory.CallInjected64<uint>(handInFunc, new object[] { instance, slot.Slot, (int)slot.BagId });
    }
}