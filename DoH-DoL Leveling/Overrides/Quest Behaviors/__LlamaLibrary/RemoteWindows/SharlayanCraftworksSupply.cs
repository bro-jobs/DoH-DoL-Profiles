using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using System.Windows.Media;
using Buddy.Coroutines;
using ff14bot;
using ff14bot.Enums;
using ff14bot.Managers;
using ff14bot.RemoteWindows;
using LlamaLibrary.Extensions;
using LlamaLibrary.Logging;
using LlamaLibrary.Memory;
using LlamaLibrary.Helpers;
using LlamaLibrary.RemoteAgents;

namespace LlamaLibrary.RemoteWindows;

public class SharlayanCraftworksSupply : RemoteWindow<SharlayanCraftworksSupply>
{

    private static readonly LLogger Log = new("InventoryUtilities", Colors.Green);
    public SharlayanCraftworksSupply() : base("SharlayanCraftworksSupply")
    {
    }

    public static readonly Dictionary<string, int> Properties = new()
    {
#if RB_DT
            {
                "TurnInItemId",
                8
            },
#else
        {
            "TurnInItemId",
            8
        },
#endif

        {
            "EsteemLevel",
            6
        },
        {
            "Esteem",
            7
        },
    };

    public int TurnInItemId => Elements[Properties["TurnInItemId"]].TrimmedData;

    public int EsteemLevel => Elements[Properties["EsteemLevel"]].TrimmedData;

    public int Esteem => Elements[Properties["Esteem"]].TrimmedData;

    public void Deliver()
    {
        SendAction(1, 3, 0);
    }

    public async Task HandOverItems()
    {

        // Debug all window elements
    Log.Information("Debugging Window Elements:");
    for (int i = 0; i < Elements.Length; i++)
    {
        Log.Information($"Element[{i}]: Raw={Elements[i].Data}, Trimmed={Elements[i].TrimmedData}");
    }

    // Debug the specific element we're using
    Log.Information($"Using element index {Properties["TurnInItemId"]} for TurnInItemId");
    var element = Elements[Properties["TurnInItemId"]];
    Log.Information($"Element details - Data: {element.Data}, TrimmedData: {element.TrimmedData}");

        // Add debugging logs
    Log.Information($"TurnInItemId: {TurnInItemId}");
    Log.Information($"Current Esteem: {Esteem}");
    Log.Information($"Looking to take {6 - Esteem} items");
    
    var matchingSlots = InventoryManager.FilledSlots.Where(i => i.TrueItemId == TurnInItemId);
    Log.Information($"Found {matchingSlots.Count()} matching items in inventory");
    
    foreach (var slot in matchingSlots)
    {
        Log.Information($"Found matching item: ID {slot.TrueItemId}, Collectability {slot.Collectability}");
    }

    var slotsToTurnIn = matchingSlots
        .OrderByDescending(i => i.Collectability)
        .Take(6 - Esteem);

    Log.Information($"Selected {slotsToTurnIn.Count()} slots for turnin");

    foreach (var slot in slotsToTurnIn)
    {
        Log.Information($"Attempting to hand in slot: {slot?.ToString() ?? "null"} at position {slot?.Slot} in bag {slot?.BagId}");
        if (slot != null)
        {
            try 
            {
                AgentSharlayanCraftworksSupply.Instance.HandIn(slot);
                Log.Information($"HandIn called successfully for slot {slot.Slot} in bag {slot.BagId}");
                await Coroutine.Sleep(700);
            }
            catch (System.Exception ex)
            {
                Log.Error($"Error during HandIn: {ex.Message}");
            }
        }
    }

    await Coroutine.Sleep(500);

    Deliver();

        await Coroutine.Wait(5000, () => Talk.DialogOpen || SelectYesno.IsOpen);

        if (SelectYesno.IsOpen)
        {
            SelectYesno.Yes();
            await Coroutine.Wait(5000, () => Talk.DialogOpen);
        }

        await GeneralFunctions.SmallTalk(5000);

        /*await Coroutine.Wait(10000, () => QuestLogManager.InCutscene);

        while (QuestLogManager.InCutscene)
        {
            AgentCutScene.Instance.PromptSkip();
            if (AgentCutScene.Instance.CanSkip && SelectString.IsOpen)
            {
                SelectString.ClickSlot(0);
            }

            await Coroutine.Yield();
        }

        await Coroutine.Wait(20000, () => JournalResult.IsOpen || Talk.DialogOpen);

        if (Talk.DialogOpen)
        {
            await GeneralFunctions.SmallTalk(1000);
            await Coroutine.Wait(20000, () => JournalResult.IsOpen);
        }

        if (JournalResult.IsOpen)
        {
            JournalAccept.Accept();
            await Coroutine.Wait(20000, () => !JournalResult.IsOpen);

            await GeneralFunctions.SmallTalk(5000);
        }
        */
    }
}